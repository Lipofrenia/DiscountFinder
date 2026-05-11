"""
services.py — логика парсинга и мониторинга цен.

ParserService:  возвращает моковые данные о товарах.
price_monitor:  фоновая задача, которая каждые 30 мин случайно
                меняет current_price у товаров в БД — имитация
                динамики цен.
"""

import random
import asyncio
import logging
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend import models
from backend.schemas import SearchResult

logger = logging.getLogger(__name__)

# ─────────────── Моковые данные ───────────────

_MOCK_WB = [
    SearchResult(
        title="Кроссовки Nike Air Max 270 мужские",
        current_price=4_290.0,
        old_price=7_999.0,
        url="https://www.wildberries.ru/catalog/12345678/detail.aspx",
        image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400",
        marketplace_name="WB",
    ),
    SearchResult(
        title="Рюкзак городской Nike Heritage",
        current_price=2_150.0,
        old_price=3_200.0,
        url="https://www.wildberries.ru/catalog/87654321/detail.aspx",
        image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400",
        marketplace_name="WB",
    ),
]

_MOCK_OZON = [
    SearchResult(
        title='Смарт-часы Xiaomi Band 8 Pro',
        current_price=5_990.0,
        old_price=8_499.0,
        url="https://www.ozon.ru/product/smartband-xiaomi-band-8-pro/",
        image_url="https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=400",
        marketplace_name="Ozon",
    ),
    SearchResult(
        title="Наушники TWS Baseus Storm2",
        current_price=1_890.0,
        old_price=2_990.0,
        url="https://www.ozon.ru/product/naushniki-baseus-storm2/",
        image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
        marketplace_name="Ozon",
    ),
]

_MOCK_YA = [
    SearchResult(
        title="Механическая клавиатура Keychron K2 Pro",
        current_price=9_450.0,
        old_price=12_990.0,
        url="https://market.yandex.ru/product--keychron-k2-pro/",
        image_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400",
        marketplace_name="Ya",
    ),
]

ALL_MOCK: List[SearchResult] = _MOCK_WB + _MOCK_OZON + _MOCK_YA


# ─────────────── Parser Service ───────────────

class ParserService:
    """
    Сервис поиска товаров.
    Сейчас методы — заглушки, возвращающие тестовые данные.
    В будущем каждый метод заменяется реальным парсером.
    """

    def search_wildberries(self, query: str) -> List[SearchResult]:
        """Заглушка WB: возвращает 2 мок-товара."""
        logger.info("[WB] поиск: %s", query)
        # Имитируем небольшую вариацию цены при каждом запросе
        results = []
        for item in _MOCK_WB:
            delta = random.uniform(-0.05, 0.05)
            results.append(item.model_copy(
                update={"current_price": round(item.current_price * (1 + delta), 2)}
            ))
        return results

    def search_ozon(self, query: str) -> List[SearchResult]:
        """Заглушка Ozon: возвращает 2 мок-товара."""
        logger.info("[Ozon] поиск: %s", query)
        results = []
        for item in _MOCK_OZON:
            delta = random.uniform(-0.05, 0.05)
            results.append(item.model_copy(
                update={"current_price": round(item.current_price * (1 + delta), 2)}
            ))
        return results

    def search_yandex(self, query: str) -> List[SearchResult]:
        """Заглушка Яндекс Маркет: возвращает 1 мок-товар."""
        logger.info("[Ya] поиск: %s", query)
        results = []
        for item in _MOCK_YA:
            delta = random.uniform(-0.05, 0.05)
            results.append(item.model_copy(
                update={"current_price": round(item.current_price * (1 + delta), 2)}
            ))
        return results

    def search_all(self, query: str) -> List[SearchResult]:
        """Агрегирует результаты со всех площадок."""
        return (
            self.search_wildberries(query)
            + self.search_ozon(query)
            + self.search_yandex(query)
        )


# ─────────────── Мониторинг цен ───────────────

async def price_monitor_loop():
    """
    Фоновая asyncio-задача.
    Каждые 30 минут случайно изменяет current_price у всех
    сохранённых товаров (±15%), имитируя динамику цен.
    """
    INTERVAL = 30 * 60  # 30 минут в секундах
    logger.info("Монитор цен запущен (интервал: %d сек)", INTERVAL)

    while True:
        await asyncio.sleep(INTERVAL)
        try:
            _apply_random_price_change()
        except Exception as exc:
            logger.error("Ошибка монитора цен: %s", exc)


def _apply_random_price_change():
    """
    Синхронная часть: открывает свою сессию БД и обновляет цены.
    Вынесена отдельно, чтобы не блокировать event loop.
    """
    db: Session = SessionLocal()
    try:
        products = db.query(models.Product).all()
        if not products:
            logger.info("Монитор: нет товаров для обновления")
            return

        for product in products:
            change = random.uniform(-0.15, 0.15)        # ±15%
            new_price = round(product.current_price * (1 + change), 2)
            new_price = max(new_price, 1.0)             # цена не ниже 1 руб.

            # Сохраняем старую цену перед обновлением
            product.old_price = product.current_price
            product.current_price = new_price
            product.last_updated = datetime.utcnow()

        db.commit()
        logger.info("Монитор: обновлено %d товаров", len(products))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
