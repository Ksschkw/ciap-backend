from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

from app.core.redis_client import get_redis_client


class RateLimiter:
    def __init__(self, limit: int = 100, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        redis_client = get_redis_client()
        client_ip = request.client.host if request.client is not None else "unknown"
        key = f"rate-limit:{client_ip}:{request.url.path}"
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, self.window_seconds)
        if current > self.limit:
            return Response(content="Too Many Requests", status_code=429)
        return await call_next(request)
