"""
main.py — точка входа FastAPI-приложения.

Маршруты:
  POST /auth/register  — регистрация
  POST /auth/login     — вход (возвращает JWT)
  GET  /search         — поиск товаров (мок)
  GET  /favorites      — список избранного текущего пользователя
  POST /favorites      — добавить товар в избранное
  DELETE /favorites/{id} — удалить товар из избранного
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from backend.database import engine, get_db, Base
from backend import models, schemas
from backend.auth import (
    hash_password, verify_password,
    create_access_token, get_current_user,
)
from backend.services import ParserService, price_monitor_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ── Lifespan: создание таблиц + запуск фонового монитора ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём таблицы в БД если их ещё нет
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД созданы / проверены")

    # Запускаем фоновый монитор цен
    monitor_task = asyncio.create_task(price_monitor_loop())
    logger.info("Фоновый монитор цен запущен")

    yield  # приложение работает

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        logger.info("Монитор цен остановлен")


app = FastAPI(
    title="Скидочный сыщик API",
    version="1.0.0",
    description="Backend для поиска и отслеживания скидок на WB, Ozon, Яндекс Маркет",
    lifespan=lifespan,
)

# CORS — разрешаем Flet-клиенту (localhost) обращаться к API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parser = ParserService()


# ════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя."""
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован",
        )
    user = models.User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Вход пользователя.
    Принимает form-data: username (= email) + password.
    Возвращает JWT-токен.
    """
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


# ════════════════════════════════════════════════
#  SEARCH
# ════════════════════════════════════════════════

@app.get("/search", response_model=List[schemas.SearchResult])
def search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Поиск товаров на всех площадках.
    После получения результатов — обновляет цены и записывает историю
    для тех товаров из избранного, чей URL совпадает с найденными.
    """
    results = parser.search_all(q)

    # Индекс результатов по URL
    results_by_url = {r.url: r for r in results}

    # Находим товары в избранном, URL которых есть в результатах поиска
    favorites = (
        db.query(models.Product)
        .filter(
            models.Product.user_id == current_user.id,
            models.Product.url.in_(results_by_url.keys()),
        )
        .all()
    )

    now = datetime.utcnow()
    for product in favorites:
        new_data = results_by_url[product.url]
        new_price = new_data.current_price

        # Записываем новую цену в историю
        history_entry = models.PriceHistory(
            product_id=product.id,
            price=new_price,
            checked_at=now,
        )
        db.add(history_entry)

        # Обновляем текущую цену (старая становится old_price)
        if product.current_price != new_price:
            product.old_price = product.current_price
            product.current_price = new_price
            product.last_updated = now

    if favorites:
        db.commit()
        logger.info(
            "[search] Обновлено цен / записана история: %d товаров", len(favorites)
        )

    return results


# ════════════════════════════════════════════════
#  FAVORITES (CRUD)
# ════════════════════════════════════════════════

@app.get("/favorites", response_model=List[schemas.ProductOut])
def get_favorites(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Список избранных товаров текущего пользователя."""
    return (
        db.query(models.Product)
        .filter(models.Product.user_id == current_user.id)
        .all()
    )


@app.post("/favorites", response_model=schemas.ProductOut, status_code=201)
def add_favorite(
    body: schemas.ProductCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Добавить товар в избранное. 409 если уже добавлен (по URL)."""
    existing = db.query(models.Product).filter(
        models.Product.user_id == current_user.id,
        models.Product.url == body.url,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Товар уже в избранном")
    product = models.Product(**body.model_dump(), user_id=current_user.id)
    db.add(product)
    db.flush()  # получаем id без commit

    # Записываем начальную цену в историю
    db.add(models.PriceHistory(
        product_id=product.id,
        price=body.current_price,
        checked_at=datetime.utcnow(),
    ))

    db.commit()
    db.refresh(product)
    return product


@app.delete("/favorites/{product_id}", status_code=204)
def delete_favorite(
    product_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удалить товар из избранного по ID."""
    product = (
        db.query(models.Product)
        .filter(
            models.Product.id == product_id,
            models.Product.user_id == current_user.id,
        )
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    db.delete(product)
    db.commit()
