"""
Abstract Base Repository
========================
All concrete repository classes inherit from IRepository.
This defines the standard CRUD contract — backend devs implement
these exactly once per ORM model, nothing more, nothing less.

Generic Type T = the SQLAlchemy ORM model (e.g., User, ContentItem).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Generic repository interface.

    Each concrete repo gets a SQLAlchemy Session injected at construction
    time via FastAPI's Depends(get_db) dependency.

    Example usage in backend service:
        user_repo = SQLUserRepository(db)
        user = user_repo.get_by_id(user_id)
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ──────────────────────────────────────────────────────────────────────
    # Core CRUD — must be implemented by every concrete repo
    # ──────────────────────────────────────────────────────────────────────

    @abstractmethod
    def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Return a single record by primary key, or None if not found."""
        ...

    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Return a paginated list of all records for this entity."""
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Persist a new record and return it with the auto-generated PK.

        The caller creates the SQLAlchemy model instance and passes it here.
        This method calls db.add(), db.commit(), db.refresh().
        """
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Merge and persist changes to an existing record.

        The caller mutates the ORM instance's fields, then passes it here.
        This method calls db.commit(), db.refresh().
        """
        ...

    @abstractmethod
    def delete(self, entity_id: UUID) -> bool:
        """
        Hard-delete a record by primary key.

        Returns True if something was deleted, False if the record didn't exist.
        NOTE: prefer soft-deletes (status='DELETED') for content/campaigns.
        """
        ...