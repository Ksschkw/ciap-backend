from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class PaginationMeta:
    page: int
    limit: int
    total_items: int
    total_pages: int


@dataclass(slots=True)
class PaginatedResult(Generic[T]):
    items: list[T]
    meta: PaginationMeta


def paginate_items(items: list[T], page: int = 1, limit: int = 20) -> PaginatedResult[T]:
    page = max(page, 1)
    limit = max(limit, 1)
    total_items = len(items)
    total_pages = max(ceil(total_items / limit), 1) if total_items else 0
    start = (page - 1) * limit
    end = start + limit
    return PaginatedResult(
        items=items[start:end],
        meta=PaginationMeta(
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
