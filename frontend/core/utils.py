def normalize_url(url: str) -> str:
    if not url:
        return ""
    base_url = url.split("?")[0]
    return base_url.rstrip("/")


def discount_pct(current: float, old: float) -> int:
    if old and old > current:
        return int((1 - current / old) * 100)
    return 0
