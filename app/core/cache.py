from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from app.core.redis_client import get_redis_client

T = TypeVar("T")


def _build_cache_key(prefix: str, function_name: str, args: tuple[object, ...], kwargs: dict[str, object]) -> str:
    payload = json.dumps({"args": args, "kwargs": kwargs}, default=str, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"cache:{prefix}:{function_name}:{digest}"


def cache_result(prefix: str, ttl_seconds: int = 300) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            redis_client = get_redis_client()
            cache_key = _build_cache_key(prefix, func.__name__, args, kwargs)
            cached_value = await redis_client.get(cache_key)
            if cached_value is not None:
                return json.loads(cached_value)

            result = await func(*args, **kwargs)
            await redis_client.set(cache_key, json.dumps(result), ex=ttl_seconds)
            return result

        return wrapper

    return decorator
