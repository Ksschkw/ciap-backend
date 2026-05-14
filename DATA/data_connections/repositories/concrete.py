"""
Concrete SQLAlchemy implementations of all DATA repository interfaces.
All methods are synchronous (standard SQLAlchemy Session).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from DATA.models.campaigns import Campaign, CampaignCollaboration, CampaignCreatorBrief, ConversionEvent
from DATA.models.content import AudienceSnapshot, ContentItem, ContentMetricSnapshot
from DATA.models.scoring import InfluenceScore
from DATA.models.users import CreatorProfile, PlatformConnection, SMEProfile, User


# ─── Base ─────────────────────────────────────────────────────────────────────

class BaseConcreteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db


# ─── User ─────────────────────────────────────────────────────────────────────

class SQLUserRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[User]:
        return self.db.query(User).filter(User.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, entity: User) -> User:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: User) -> User:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        u = self.get_by_id(entity_id)
        if not u:
            return False
        self.db.delete(u); self.db.commit(); return True

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).filter(User.role == role).offset(skip).limit(limit).all()

    def update_last_login(self, user_id: Any, timestamp: datetime) -> None:
        u = self.get_by_id(user_id)
        if u:
            u.last_login_at = timestamp  # type: ignore[assignment]
            self.db.commit()

    def verify_email(self, user_id: Any) -> None:
        u = self.get_by_id(user_id)
        if u:
            u.is_email_verified = True  # type: ignore[assignment]
            u.status = "ACTIVE"  # type: ignore[assignment]
            self.db.commit()

    def update_subscription(self, user_id: Any, plan: str) -> User:
        u = self.get_by_id(user_id)
        if u is None:
            raise ValueError(f"User not found: {user_id}")
        u.subscription_plan = plan  # type: ignore[assignment]
        self.db.commit(); self.db.refresh(u); return u

    def add(self, entity: User) -> None:
        self.db.add(entity); self.db.flush()


# ─── Creator Profile ──────────────────────────────────────────────────────────

class SQLCreatorProfileRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[CreatorProfile]:
        return self.db.query(CreatorProfile).filter(CreatorProfile.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[CreatorProfile]:
        return self.db.query(CreatorProfile).offset(skip).limit(limit).all()

    def create(self, entity: CreatorProfile) -> CreatorProfile:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: CreatorProfile) -> CreatorProfile:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    def get_by_user_id(self, user_id: Any) -> Optional[CreatorProfile]:
        return self.db.query(CreatorProfile).filter(CreatorProfile.user_id == user_id).first()

    def list_public(self, limit: int = 1000, offset: int = 0) -> List[CreatorProfile]:
        """Legacy method kept for compatibility. Prefer search_creators() for new code."""
        return (
            self.db.query(CreatorProfile)
            .filter(CreatorProfile.is_public == True)  # noqa: E712
            .offset(offset)
            .limit(limit)
            .all()
        )

    # Called by old interface names (keep both for compatibility)
    def list_public_creators(self, *args: Any, **kwargs: Any) -> List[CreatorProfile]:
        return self.list_public()

    def search_creators(
        self,
        query: Optional[str] = None,
        niche: Optional[str] = None,
        location: Optional[str] = None,
        platform: Optional[str] = None,
        min_followers: Optional[int] = None,
        max_followers: Optional[int] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        sort_by: str = "influence_score",
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[CreatorProfile], int]:
        """
        Execute all filtering, sorting, and pagination directly in the database.
        Returns (items, total_count) so callers can build pagination metadata.

        Sorting columns:
          - influence_score  → CreatorProfile.influence_score DESC
          - total_followers  → CreatorProfile.total_followers DESC
          - engagement_rate  → CreatorProfile.avg_engagement_rate DESC
        """
        from sqlalchemy import func, or_, String as SAString
        from DATA.models.users import User as UserModel, PlatformConnection as PlatformConnectionModel

        q = (
            self.db.query(CreatorProfile, UserModel)
            .join(UserModel, UserModel.id == CreatorProfile.user_id)
            .filter(CreatorProfile.is_public == True)  # noqa: E712
        )

        # ── Text search ───────────────────────────────────────────────────────
        if query:
            lowered = f"%{query.lower()}%"
            q = q.filter(
                or_(
                    func.lower(UserModel.full_name).like(lowered),
                    func.lower(CreatorProfile.category).like(lowered),
                )
            )

        # ── Exact / range filters ─────────────────────────────────────────────
        if niche:
            q = q.filter(func.lower(CreatorProfile.category) == niche.lower())
        if location:
            q = q.filter(
                or_(
                    func.lower(CreatorProfile.location_country) == location.lower(),
                    func.lower(CreatorProfile.location_city) == location.lower(),
                )
            )
        if platform:
            # Sub-query: user has a platform connection with this platform name
            platform_sub = (
                self.db.query(PlatformConnectionModel.user_id)
                .filter(func.lower(PlatformConnectionModel.platform_name) == platform.lower())
                .subquery()
            )
            q = q.filter(CreatorProfile.user_id.in_(platform_sub))
        if min_followers is not None:
            q = q.filter(CreatorProfile.total_followers >= min_followers)
        if max_followers is not None:
            q = q.filter(CreatorProfile.total_followers <= max_followers)
        if min_score is not None:
            q = q.filter(CreatorProfile.influence_score >= min_score)
        if max_score is not None:
            q = q.filter(CreatorProfile.influence_score <= max_score)

        # ── Count (before pagination) ─────────────────────────────────────────
        total_count: int = q.count()

        # ── Sorting ───────────────────────────────────────────────────────────
        _sort_map = {
            "influence_score": CreatorProfile.influence_score.desc(),
            "total_followers":  CreatorProfile.total_followers.desc(),
            "followers":        CreatorProfile.total_followers.desc(),
            "engagement_rate":  CreatorProfile.avg_engagement_rate.desc(),
        }
        sort_clause = _sort_map.get(sort_by, CreatorProfile.influence_score.desc())
        q = q.order_by(sort_clause)

        # ── Pagination ────────────────────────────────────────────────────────
        offset = (page - 1) * limit
        rows = q.offset(offset).limit(limit).all()

        # rows is a list of (CreatorProfile, User) tuples; attach the user to
        # the profile so callers can access it without extra queries.
        for profile, user in rows:
            profile._cached_user = user  # type: ignore[attr-defined]

        profiles = [profile for profile, _ in rows]
        return profiles, total_count

    def update_influence_score(self, creator_id: Any, score: float, avg_engagement_rate: float) -> None:
        p = self.get_by_user_id(creator_id)
        if p:
            p.influence_score = score  # type: ignore[assignment]
            p.avg_engagement_rate = avg_engagement_rate  # type: ignore[assignment]
            self.db.commit()

    def update_total_followers(self, creator_id: Any, total: int) -> None:
        p = self.get_by_user_id(creator_id)
        if p:
            p.total_followers = total  # type: ignore[assignment]
            self.db.commit()


# ─── SME Profile ──────────────────────────────────────────────────────────────

class SQLSMEProfileRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[SMEProfile]:
        return self.db.query(SMEProfile).filter(SMEProfile.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[SMEProfile]:
        return self.db.query(SMEProfile).offset(skip).limit(limit).all()

    def create(self, entity: SMEProfile) -> SMEProfile:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: SMEProfile) -> SMEProfile:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    def get_by_user_id(self, user_id: Any) -> Optional[SMEProfile]:
        return self.db.query(SMEProfile).filter(SMEProfile.user_id == user_id).first()

    def get_by_industry(self, industry: str, skip: int = 0, limit: int = 50) -> List[SMEProfile]:
        return self.db.query(SMEProfile).filter(SMEProfile.industry == industry).offset(skip).limit(limit).all()


# ─── Platform Connection ──────────────────────────────────────────────────────

class SQLPlatformConnectionRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[PlatformConnection]:
        return self.db.query(PlatformConnection).filter(PlatformConnection.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[PlatformConnection]:
        return self.db.query(PlatformConnection).offset(skip).limit(limit).all()

    def create(self, entity: PlatformConnection) -> PlatformConnection:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: PlatformConnection) -> PlatformConnection:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    def get_by_user_and_platform(self, user_id: Any, platform_name: str) -> Optional[PlatformConnection]:
        return (
            self.db.query(PlatformConnection)
            .filter(PlatformConnection.user_id == user_id, PlatformConnection.platform_name == platform_name)
            .first()
        )

    # Called by DiscoverService and PlatformService
    def list_for_user(self, user_id: Any) -> List[PlatformConnection]:
        return (
            self.db.query(PlatformConnection)
            .filter(PlatformConnection.user_id == user_id)
            .all()
        )

    # Interface alias
    def get_active_connections_for_user(self, user_id: Any) -> List[PlatformConnection]:
        return self.list_for_user(user_id)

    def get_all_expiring_soon(self, within_minutes: int = 30) -> List[PlatformConnection]:
        return []

    def update_tokens(self, connection_id: Any, new_access_token: str, new_refresh_token: Optional[str], new_expires_at: Optional[datetime]) -> Optional[PlatformConnection]:
        conn = self.get_by_id(connection_id)
        if conn:
            conn.access_token = new_access_token  # type: ignore[assignment]
            if new_refresh_token:
                conn.refresh_token = new_refresh_token  # type: ignore[assignment]
            if new_expires_at:
                conn.token_expires_at = new_expires_at  # type: ignore[assignment]
            self.db.commit(); self.db.refresh(conn)
        return conn

    def mark_inactive(self, connection_id: Any, error_message: str) -> None:
        conn = self.get_by_id(connection_id)
        if conn:
            conn.is_active = False  # type: ignore[assignment]
            conn.sync_error_message = error_message  # type: ignore[assignment]
            self.db.commit()

    def update_last_synced(self, connection_id: Any, timestamp: datetime) -> None:
        conn = self.get_by_id(connection_id)
        if conn:
            conn.last_synced_at = timestamp  # type: ignore[assignment]
            self.db.commit()


# ─── Campaign ─────────────────────────────────────────────────────────────────

class SQLCampaignRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[Campaign]:
        return self.db.query(Campaign).filter(Campaign.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        return self.db.query(Campaign).offset(skip).limit(limit).all()

    def create(self, entity: Campaign) -> Campaign:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: Campaign) -> Campaign:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    def get_by_owner(self, sme_id: Any, limit: int = 20, offset: int = 0) -> List[Campaign]:
        return self.db.query(Campaign).filter(Campaign.sme_id == sme_id).offset(offset).limit(limit).all()

    def search(self, *args: Any, **kwargs: Any) -> List[Campaign]:
        return self.db.query(Campaign).filter(Campaign.status == "ACTIVE").all()

    def update_status(self, campaign_id: Any, status: str) -> Optional[Campaign]:
        c = self.get_by_id(campaign_id)
        if c:
            c.status = status  # type: ignore[assignment]
            self.db.commit(); self.db.refresh(c)
        return c

    def update_spent_budget(self, campaign_id: Any, additional_spend: float) -> None:
        pass


# ─── Content ──────────────────────────────────────────────────────────────────

class SQLContentRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[ContentItem]:
        return self.db.query(ContentItem).filter(ContentItem.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ContentItem]:
        return self.db.query(ContentItem).offset(skip).limit(limit).all()

    def create(self, entity: ContentItem) -> ContentItem:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: ContentItem) -> ContentItem:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    # Called by DiscoverService.get_creator_detail()
    def get_by_creator(self, creator_id: Any, limit: int = 10, offset: int = 0) -> List[ContentItem]:
        return (
            self.db.query(ContentItem)
            .filter(ContentItem.creator_id == creator_id)
            .order_by(ContentItem.posted_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_creator_and_platform(self, creator_id: Any, platform: str) -> List[ContentItem]:
        return (
            self.db.query(ContentItem)
            .filter(ContentItem.creator_id == creator_id, ContentItem.platform == platform)
            .all()
        )

    def get_recent_for_creator(self, creator_id: Any, limit: int = 10) -> List[ContentItem]:
        return self.get_by_creator(creator_id, limit=limit)

    def get_by_external_id(self, platform: str, external_id: str) -> Optional[ContentItem]:
        return (
            self.db.query(ContentItem)
            .filter(ContentItem.platform == platform, ContentItem.external_id == external_id)
            .first()
        )

    def upsert_by_external_id(self, entity: ContentItem) -> ContentItem:
        """Insert or update based on (platform, external_id). Used by ingestion."""
        existing = self.get_by_external_id(str(entity.platform), str(entity.external_id))  # type: ignore[arg-type]
        if existing:
            for col in ("title", "caption", "hashtags", "permalink", "thumbnail_url", "duration_seconds", "synced_at"):
                setattr(existing, col, getattr(entity, col))
            self.db.commit(); self.db.refresh(existing); return existing
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity


# ─── Influence Score ──────────────────────────────────────────────────────────

class SQLInfluenceScoreRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[InfluenceScore]:
        return self.db.query(InfluenceScore).filter(InfluenceScore.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[InfluenceScore]:
        return self.db.query(InfluenceScore).offset(skip).limit(limit).all()

    def create(self, entity: InfluenceScore) -> InfluenceScore:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: InfluenceScore) -> InfluenceScore:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    # Called by DiscoverService
    def latest_for_creator(self, creator_id: Any) -> Optional[InfluenceScore]:
        return (
            self.db.query(InfluenceScore)
            .filter(InfluenceScore.creator_id == creator_id)
            .order_by(InfluenceScore.scored_at.desc())
            .first()
        )

    # Interface alias
    def get_latest_for_creator(self, creator_id: Any) -> Optional[InfluenceScore]:
        return self.latest_for_creator(creator_id)

    def get_history_for_creator(self, creator_id: Any, limit: int = 52) -> List[InfluenceScore]:
        return (
            self.db.query(InfluenceScore)
            .filter(InfluenceScore.creator_id == creator_id)
            .order_by(InfluenceScore.scored_at.desc())
            .limit(limit)
            .all()
        )

    def insert_score(self, score: InfluenceScore) -> InfluenceScore:
        return self.create(score)

    def get_top_creators(self, category: Optional[str] = None, location: Optional[str] = None, limit: int = 20) -> List[InfluenceScore]:
        return self.db.query(InfluenceScore).order_by(InfluenceScore.score.desc()).limit(limit).all()


# ─── Audience Snapshot ────────────────────────────────────────────────────────

class SQLAudienceSnapshotRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[AudienceSnapshot]:
        return self.db.query(AudienceSnapshot).filter(AudienceSnapshot.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[AudienceSnapshot]:
        return self.db.query(AudienceSnapshot).offset(skip).limit(limit).all()

    def create(self, entity: AudienceSnapshot) -> AudienceSnapshot:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: AudienceSnapshot) -> AudienceSnapshot:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    # Called by DiscoverService
    def latest_for_creator(self, creator_id: Any) -> Optional[AudienceSnapshot]:
        return (
            self.db.query(AudienceSnapshot)
            .filter(AudienceSnapshot.creator_id == creator_id)
            .order_by(AudienceSnapshot.captured_at.desc())
            .first()
        )

    # Interface alias
    def get_latest_for_creator(self, creator_id: Any) -> Optional[AudienceSnapshot]:
        return self.latest_for_creator(creator_id)

    def get_latest_for_platform(self, creator_id: Any, platform: str) -> Optional[AudienceSnapshot]:
        return (
            self.db.query(AudienceSnapshot)
            .filter(AudienceSnapshot.creator_id == creator_id, AudienceSnapshot.platform_connection_id == platform)
            .first()
        )

    def insert_snapshot(self, snapshot: AudienceSnapshot) -> AudienceSnapshot:
        return self.create(snapshot)

    def get_history(self, creator_id: Any, platform: Optional[str] = None, limit: int = 12) -> List[AudienceSnapshot]:
        return (
            self.db.query(AudienceSnapshot)
            .filter(AudienceSnapshot.creator_id == creator_id)
            .order_by(AudienceSnapshot.captured_at.desc())
            .limit(limit)
            .all()
        )


# ─── Content Metric Snapshot ──────────────────────────────────────────────────

class SQLContentMetricRepository(BaseConcreteRepository):
    def get_by_id(self, id: Any) -> Optional[ContentMetricSnapshot]:
        return self.db.query(ContentMetricSnapshot).filter(ContentMetricSnapshot.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ContentMetricSnapshot]:
        return self.db.query(ContentMetricSnapshot).offset(skip).limit(limit).all()

    def create(self, entity: ContentMetricSnapshot) -> ContentMetricSnapshot:
        self.db.add(entity); self.db.commit(); self.db.refresh(entity); return entity

    def update(self, entity: ContentMetricSnapshot) -> ContentMetricSnapshot:
        self.db.commit(); self.db.refresh(entity); return entity

    def delete(self, entity_id: Any) -> bool:
        return False

    def get_latest_for_content(self, content_id: Any) -> Optional[ContentMetricSnapshot]:
        return (
            self.db.query(ContentMetricSnapshot)
            .filter(ContentMetricSnapshot.content_id == content_id)
            .order_by(ContentMetricSnapshot.captured_at.desc())
            .first()
        )

    def insert_snapshot(self, snapshot: ContentMetricSnapshot) -> ContentMetricSnapshot:
        return self.create(snapshot)

    def get_history(self, content_id: Any, limit: int = 30) -> List[ContentMetricSnapshot]:
        return (
            self.db.query(ContentMetricSnapshot)
            .filter(ContentMetricSnapshot.content_id == content_id)
            .order_by(ContentMetricSnapshot.captured_at.desc())
            .limit(limit)
            .all()
        )

    # ── Called by analytics_service / campaign_service ──────────────────────
    def latest_for_user(self, creator_id: Any) -> Optional[ContentMetricSnapshot]:
        """Return the single most recent metric snapshot across all content for a creator."""
        from sqlalchemy import select
        content_ids = select(ContentItem.id).where(ContentItem.creator_id == creator_id)
        return (
            self.db.query(ContentMetricSnapshot)
            .filter(ContentMetricSnapshot.content_id.in_(content_ids))
            .order_by(ContentMetricSnapshot.captured_at.desc())
            .first()
        )

    def list_for_user(self, creator_id: Any, limit: int = 10, offset: int = 0) -> List[ContentMetricSnapshot]:
        """Return recent metric snapshots (across all content) for a creator, newest first."""
        from sqlalchemy import select
        content_ids = select(ContentItem.id).where(ContentItem.creator_id == creator_id)
        return (
            self.db.query(ContentMetricSnapshot)
            .filter(ContentMetricSnapshot.content_id.in_(content_ids))
            .order_by(ContentMetricSnapshot.captured_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_aggregated_for_creator(self, creator_id: Any) -> dict:
        """Return SUM/AVG of all metrics across all content items for a creator.
        Uses the actual ContentMetricSnapshot columns, not a JSON blob.
        """
        from sqlalchemy import select
        content_ids = select(ContentItem.id).where(ContentItem.creator_id == creator_id)
        snapshots = (
            self.db.query(ContentMetricSnapshot)
            .filter(ContentMetricSnapshot.content_id.in_(content_ids))
            .all()
        )
        total_views = total_likes = total_comments = total_shares = 0
        for s in snapshots:
            total_views    += int(s.views    or 0)
            total_likes    += int(s.likes    or 0)
            total_comments += int(s.comments or 0)
            total_shares   += int(s.shares   or 0)
        avg_engagement = round(total_likes / max(total_views, 1), 4)
        return {
            "total_views":         total_views,
            "total_likes":         total_likes,
            "total_comments":      total_comments,
            "total_shares":        total_shares,
            "avg_engagement_rate": avg_engagement,
        }

