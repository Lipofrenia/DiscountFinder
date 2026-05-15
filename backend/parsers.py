import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import List

# Добавляем корень проекта в sys.path, чтобы импорты типа 'from backend...' работали
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from playwright.sync_api import sync_playwright

try:
    from backend.schemas import SearchResult
except ImportError:
    # На случай если всё же не подхватилось при прямом запуске
    SearchResult = None 

# Фикс для Windows (для работы как самостоятельный скрипт)
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except:
        pass

logger = logging.getLogger(__name__)

def search_yandex_market_standalone(query: str):
    """
    Ваш рабочий код 1-в-1. 
    Запускается в отдельном процессе для обхода ограничений Windows.
    """
    if not query:
        return []

    results = []
    timestamp = datetime.now().isoformat()

    try:
        with sync_playwright() as p:
            # headless=False для видимости
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Ищем
            url = f"https://market.yandex.ru/search?text={query.replace(' ', '%20')}"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            page.wait_for_timeout(4000)  # даём загрузиться

            # Скроллим
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            cards = page.query_selector_all('div[data-zone-name="productSnippet"]')

            for card in cards:
                try:
                    title_el = card.query_selector('span[data-auto="snippet-title"]')
                    title = title_el.inner_text() if title_el else None

                    link_el = card.query_selector('a[data-auto="snippet-link"]')
                    relative_url = link_el.get_attribute('href') if link_el else None
                    product_url = f"https://market.yandex.ru{relative_url}" if relative_url else None

                    current_price_el = card.query_selector('span[data-auto="snippet-price-current"]')
                    current_price = current_price_el.inner_text() if current_price_el else None

                    old_price_el = card.query_selector('span[class*="oldPrice"], span[style*="text-decoration: line-through"]')
                    old_price = old_price_el.inner_text() if old_price_el else None

                    img_el = card.query_selector('img.w7Bf7')
                    image_url = img_el.get_attribute('src') if img_el else None

                    rating_el = card.query_selector('span.ds-rating__value')
                    rating = rating_el.inner_text() if rating_el else None

                    if title and current_price and product_url:
                        results.append({
                            "title": title.strip(),
                            "current_price": current_price.strip(),
                            "old_price": old_price.strip() if old_price else None,
                            "product_url": product_url,
                            "image_url": image_url,
                            "marketplace_name": "Ya",
                            "rating": rating.strip() if rating else None,
                        })

                except Exception:
                    continue

            browser.close()
    except Exception as exc:
        # В режиме скрипта выводим ошибку в stderr
        sys.stderr.write(f"Error: {exc}\n")

    return results

if __name__ == "__main__":
    # Если запущен как скрипт: python -m backend.parsers "запрос"
    if len(sys.argv) > 1:
        # Принудительно устанавливаем UTF-8 для stdout на Windows, 
        # чтобы избежать UnicodeEncodeError при печати спецсимволов
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
            
        search_query = sys.argv[1]
        results_list = search_yandex_market_standalone(search_query)
        # Выводим только JSON в stdout для перехвата
        print(json.dumps(results_list, ensure_ascii=False))
