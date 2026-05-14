"""
User Domain Repositories
========================
Covers: User, CreatorProfile, SMEProfile, PlatformConnection

Matches ERD tables:
    users               → IUserRepository
    creator_profiles    → ICreatorProfileRepository
    sme_profiles        → ISMEProfileRepository
    platform_connections→ IPlatformConnectionRepository

Backend dev: implement each interface as a concrete SQLAlchemy class.
See the example SQLUserRepository at the bottom of this file.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Any, List, Optional, cast
from uuid import UUID

from sqlalchemy.orm import Session

from DATA.data_connections.repositories.base import IRepository
from DATA.models.users import (
    CreatorProfile,
    PlatformConnection,
    SMEProfile,
    User,
)


# ══════════════════════════════════════════════════════════════════════════════
# IUserRepository — users table
# ══════════════════════════════════════════════════════════════════════════════

class IUserRepository(IRepository[User]):
    """CRUD contract for the `users` table."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by unique email. Used during login."""
        ...

    @abstractmethod
    def get_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        """List users filtered by role (CREATOR | SME | AGENCY | ADMIN)."""
        ...

    @abstractmethod
    def update_last_login(self, user_id: UUID, timestamp: datetime) -> None:
        """Called on every successful login to keep last_login_at fresh."""
        ...

    @abstractmethod
    def verify_email(self, user_id: UUID) -> None:
        """Set is_email_verified=True and status=ACTIVE after email confirmation."""
        ...

    @abstractmethod
    def update_subscription(self, user_id: UUID, plan: str) -> User:
        """Change subscription tier. Called by the payment webhook service."""
        ...


# ══════════════════════════════════════════════════════════════════════════════
# ICreatorProfileRepository — creator_profiles table
# ══════════════════════════════════════════════════════════════════════════════

class ICreatorProfileRepository(IRepository[CreatorProfile]):
    """CRUD contract for the `creator_profiles` table."""

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> Optional[CreatorProfile]:
        """1-to-1 lookup: given User.id, return the CreatorProfile."""
        ...

    @abstractmethod
    def list_public_creators(
        self,
        category: Optional[str] = None,
        location_country: Optional[str] = None,
        min_influence_score: Optional[float] = None,
        min_followers: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[CreatorProfile]:
        """
        SME Discovery query — returns only is_public=True profiles.
        Supports optional filters matching Campaign.target_* fields.

        Ordered by influence_score DESC.
        """
        ...

    @abstractmethod
    def update_influence_score(
        self, creator_id: UUID, score: float, avg_engagement_rate: float
    ) -> None:
        """
        Denormalised update — called by the ML scoring service weekly.
        Updates CreatorProfile.influence_score and .avg_engagement_rate.
        """
        ...

    @abstractmethod
    def update_total_followers(self, creator_id: UUID, total: int) -> None:
        """
        Denormalised update — called by ingestion service after each sync.
        Aggregates follower counts across all PlatformConnections.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# ISMEProfileRepository — sme_profiles table
# ══════════════════════════════════════════════════════════════════════════════

class ISMEProfileRepository(IRepository[SMEProfile]):
    """CRUD contract for the `sme_profiles` table."""

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> Optional[SMEProfile]:
        """1-to-1 lookup: given User.id, return the SMEProfile."""
        ...

    @abstractmethod
    def get_by_industry(self, industry: str, skip: int = 0, limit: int = 50) -> List[SMEProfile]:
        """List SME profiles by industry. Used for admin analytics."""
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IPlatformConnectionRepository — platform_connections table
# ══════════════════════════════════════════════════════════════════════════════

class IPlatformConnectionRepository(IRepository[PlatformConnection]):
    """
    CRUD contract for the `platform_connections` table.

    SECURITY: access_token and refresh_token stored here are ENCRYPTED.
    The ingestion service must decrypt them before passing to API clients.
    Never log these values.
    """

    @abstractmethod
    def get_by_user_and_platform(
        self, user_id: UUID, platform_name: str
    ) -> Optional[PlatformConnection]:
        """
        Unique composite lookup — one connection per user per platform.
        Returns None if the user hasn't connected this platform yet.
        """
        ...

    @abstractmethod
    def get_active_connections_for_user(self, user_id: UUID) -> List[PlatformConnection]:
        """
        Return all is_active=True connections for a user.
        Used by the ingestion service to know which platforms need syncing.
        """
        ...

    @abstractmethod
    def get_all_expiring_soon(self, within_minutes: int = 30) -> List[PlatformConnection]:
        """
        Returns connections where token_expires_at is within `within_minutes`.
        Used by the scheduled token refresh job (runs every 15 minutes).
        """
        ...

    @abstractmethod
    def update_tokens(
        self,
        connection_id: UUID,
        new_access_token: str,
        new_refresh_token: Optional[str],
        new_expires_at: Optional[datetime],
    ) -> PlatformConnection:
        """
        Replace stored tokens after a successful OAuth refresh.
        Tokens must already be ENCRYPTED by the caller before this call.
        """
        ...

    @abstractmethod
    def mark_inactive(self, connection_id: UUID, error_message: str) -> None:
        """
        Set is_active=False and store the error message.
        Called when token refresh fails permanently (user revoked access).
        """
        ...

    @abstractmethod
    def update_last_synced(self, connection_id: UUID, timestamp: datetime) -> None:
        """Called at the end of every successful data ingestion run."""
        ...


# ══════════════════════════════════════════════════════════════════════════════
# CONCRETE EXAMPLE — SQLUserRepository
# Backend dev: copy this pattern for every interface above
# ══════════════════════════════════════════════════════════════════════════════

class SQLUserRepository(IUserRepository):
    """
    Concrete SQLAlchemy implementation of IUserRepository.

    Backend dev copies this pattern to implement ISMEProfileRepository,
    ICreatorProfileRepository, and IPlatformConnectionRepository.
    """

    def get_by_id(self, entity_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == entity_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, entity: User) -> User:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: User) -> User:
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity_id: UUID) -> bool:
        user = self.get_by_id(entity_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            self.db.query(User)
            .filter(User.role == role)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_last_login(self, user_id: UUID, timestamp: datetime) -> None:
        user = self.get_by_id(user_id)
        if user:
            user_any = cast(Any, user)
            user_any.last_login_at = timestamp
            self.db.commit()

    def verify_email(self, user_id: UUID) -> None:
        user = self.get_by_id(user_id)
        if user:
            user_any = cast(Any, user)
            user_any.is_email_verified = True
            user_any.status = "ACTIVE"
            self.db.commit()

    def update_subscription(self, user_id: UUID, plan: str) -> User:
        user = self.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")
        user_any = cast(Any, user)
        user_any.subscription_plan = plan
        self.db.commit()
        self.db.refresh(user)
        return user