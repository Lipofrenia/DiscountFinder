def normalize_url(url: str) -> str:
    """
    Очищает URL от технических параметров (после ?), чтобы 
    сравнение товаров было более надежным.
    """
    if not url:
        return ""
    # Отрезаем всё после знака вопроса (параметры поиска, трекинга и т.д.)
    base_url = url.split("?")[0]
    # Убираем слеш в конце для единообразия
    return base_url.rstrip("/")


def discount_pct(current: float, old: float) -> int:
    """Считает процент скидки."""
    if old and old > current:
        return int((1 - current / old) * 100)
    return 0
