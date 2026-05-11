"""
database.py — подключение к PostgreSQL через SQLAlchemy.
Читает DATABASE_URL из .env файла.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Загружаем .env из корня проекта (на уровень выше backend/)
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/discount_db",  # fallback
)

if "password" in DATABASE_URL and not os.getenv("DATABASE_URL"):
    import warnings
    warnings.warn(
        "DATABASE_URL не задан в .env — используется заглушка. "
        "Создайте файл .env с DATABASE_URL."
    )

engine = create_engine(DATABASE_URL, echo=False)

# autocommit=False — мы сами управляем транзакциями
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


def get_db():
    """
    Dependency для FastAPI: открывает сессию на время запроса,
    затем гарантированно закрывает её.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
