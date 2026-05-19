import httpx
from .constants import API_BASE

_http_client = httpx.Client(
    trust_env=False,
    timeout=60,
)


def api(method: str, path: str, token: str = None, **kwargs):
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
    try:
        return resp.json()
    except Exception:
        return {}
