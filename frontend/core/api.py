import httpx
from .constants import API_BASE

# HTTP-клиент: trust_env=False чтобы обойти корпоративный прокси
_http_client = httpx.Client(
    trust_env=False,          # не читать HTTP_PROXY / HTTPS_PROXY из env
    timeout=60,               # Увеличено до 60с для долгого парсинга
)


def api(method: str, path: str, token: str = None, **kwargs):
    """Обёртка над httpx — выполняет запрос к API."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = _http_client.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            **kwargs,
        )
        return resp
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.TimeoutException):
        return None


def safe_json(resp) -> dict:
    """Безопасно парсит JSON из ответа; при ошибке возвращает {}."""
    try:
        return resp.json()
    except Exception:
        return {}
