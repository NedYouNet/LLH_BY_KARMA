"""
Ограничение частоты запросов (защита от перебора паролей и спама регистрациями).

Алгоритм «скользящее окно»: для каждого ключа (IP или email) храним время последних
запросов; если за окно их больше лимита — отвечаем 429 Too Many Requests
с заголовком Retry-After (через сколько секунд можно повторить).

Хранилище — память процесса. Для одного сервера на хакатоне этого достаточно.
При нескольких серверах лимиты переносятся в Redis — интерфейс `hit()` не изменится.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError


class TooManyRequests(AppError):
    status_code, code = 429, "TOO_MANY_REQUESTS"


class SlidingWindowLimiter:
    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        """Регистрирует попытку. Возвращает None (можно) или сколько секунд ждать."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_seconds:
                q.popleft()
            if len(q) >= limit:
                return int(q[0] + window_seconds - now) + 1
            q.append(now)
            return None

    def count(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._hits.get(key)
            return sum(1 for t in q if t > now - window_seconds) if q else 0

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(key: str, limit: int, window_seconds: int, message: str = "Слишком много запросов. Попробуйте позже") -> None:
    if not settings.rate_limit_enabled:
        return
    retry = limiter.hit(key, limit, window_seconds)
    if retry is not None:
        raise TooManyRequests(message, extra={"retry_after": retry}, headers={"Retry-After": str(retry)})
