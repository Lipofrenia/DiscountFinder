

import random
import asyncio
import logging
import json
import sys
import subprocess
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend import models
from backend.schemas import SearchResult

logger = logging.getLogger(__name__)

def _clean_price(price_str: str) -> float:
    if not price_str:
        return 0.0
    cleaned = "".join(c for c in price_str if c.isdigit() or c in ".,")
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class ParserService:

    async def search_wildberries(self, query: str) -> List[SearchResult]:
        return []

    async def search_ozon(self, query: str) -> List[SearchResult]:
        return []

    async def search_yandex(self, query: str) -> List[SearchResult]:
        logger.info("[Ya] Запуск процесса парсинга для: %s", query)
        
        cmd = [sys.executable, "-m", "backend.parsers", query]
        
        try:
            def run_proc():
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                if result.stderr:
                    logger.error("[Ya] Скрипт парсера выдал ошибки в stderr: %s", result.stderr)
                return result.stdout

            output = await asyncio.to_thread(run_proc)
            
            if not output or not output.strip():
                logger.warning("[Ya] Парсер вернул пустой ответ (stdout пуст)")
                return []


            start_idx = output.find("[")
            if start_idx == -1:
                logger.error("[Ya] Не удалось найти начало JSON в ответе: %s", output)
                return []
            
            json_str = output[start_idx:]
            raw_items = json.loads(json_str)
            
            results = []
            for item in raw_items:
                results.append(SearchResult(
                    title=item["title"],
                    current_price=_clean_price(item["current_price"]),
                    old_price=_clean_price(item["old_price"]) if item["old_price"] else None,
                    url=item["product_url"],
                    image_url=item["image_url"],
                    marketplace_name=item["marketplace_name"],
                    rating=float(item["rating"].replace(",", ".")) if item["rating"] and isinstance(item["rating"], str) else (float(item["rating"]) if item["rating"] else None),
                    reviews_count=None
                ))
            return results

        except Exception as exc:
            logger.error("[Ya] Ошибка при запуске процесса парсера: %s", exc)
            return []

    async def search_all(self, query: str) -> List[SearchResult]:
        tasks = [
            self.search_wildberries(query),
            self.search_ozon(query),
            self.search_yandex(query)
        ]
        all_results = await asyncio.gather(*tasks)
        return [item for sublist in all_results for item in sublist]



async def price_monitor_loop():
    INTERVAL = 30 * 60
    logger.info("Монитор цен запущен")
    while True:
        await asyncio.sleep(INTERVAL)
        try:
            _apply_random_price_change()
        except Exception as exc:
            logger.error("Ошибка монитора цен: %s", exc)

def _apply_random_price_change():
    db: Session = SessionLocal()
    try:
        products = db.query(models.Product).all()
        if not products: return
        now = datetime.utcnow()
        for product in products:
            change = random.uniform(-0.15, 0.15)
            new_price = round(product.current_price * (1 + change), 2)
            new_price = max(new_price, 1.0)
            product.old_price = product.current_price
            product.current_price = new_price
            product.last_updated = now
            db.add(models.PriceHistory(product_id=product.id, price=new_price, checked_at=now))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
