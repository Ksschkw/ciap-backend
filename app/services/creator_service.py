from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from DATA.data_connections.repositories import (
    SQLAudienceSnapshotRepository,
    SQLContentRepository,
    SQLCreatorProfileRepository,
    SQLInfluenceScoreRepository,
    SQLContentMetricRepository,
    SQLPlatformConnectionRepository,
    SQLUserRepository,
)
from app.ml.audience_segmenter import AudienceSegmenter
from app.utils.pagination import paginate_items
from app.utils.date_utils import isoformat
from app.utils.serialization import model_to_dict


def _followers(profile: Any) -> int:
    return int(getattr(profile, "total_followers", None) or getattr(profile, "followers", None) or 0)

def _social(profile: Any) -> dict:
    return getattr(profile, "social_handles", None) or getattr(profile, "social_links", None) or {}

def _location(profile: Any) -> str | None:
    city    = getattr(profile, "location_city", None)
    country = getattr(profile, "location_country", None)
    legacy  = getattr(profile, "location", None)
    if city and country: return f"{city}, {country}"
    return city or country or legacy or None


@dataclass(slots=True)
class CreatorService:
    session: Session

    def get_dashboard(self, creator_id: UUID) -> dict[str, Any]:
        user_repo    = SQLUserRepository(self.session)
        profile_repo = SQLCreatorProfileRepository(self.session)
        metric_repo  = SQLContentMetricRepository(self.session)
        score_repo   = SQLInfluenceScoreRepository(self.session)
        token_repo   = SQLPlatformConnectionRepository(self.session)

        user = user_repo.get_by_id(creator_id)
        if user is None:
            raise NotFoundError("Creator not found")

        profile    = profile_repo.get_by_user_id(creator_id)
        profile_id = profile.id if profile else creator_id

        latest_score = score_repo.latest_for_creator(profile_id)
        aggregated   = metric_repo.get_aggregated_for_creator(profile_id)
        recent       = metric_repo.list_for_user(profile_id, limit=8, offset=0)
        platforms    = token_repo.list_for_user(creator_id)

        trend = [
            {"date": isoformat(m.captured_at), "views": int(m.views or 0), "likes": int(m.likes or 0)}
            for m in reversed(recent)
        ]

        return {
            "success": True,
            "message": "Creator dashboard retrieved",
            "data": {
                "creator": {
                    "id":              str(creator_id),
                    "full_name":       user.full_name or user.email,
                    "avatar_url":      user.avatar_url,
                    "category":        profile.category  if profile else None,
                    "location":        _location(profile) if profile else None,
                    "followers":       _followers(profile) if profile else 0,
                    "influence_score": latest_score.score if latest_score else 0.0,
                },
                "summary": {
                    "total_views":     aggregated.get("total_views", 0),
                    "total_likes":     aggregated.get("total_likes", 0),
                    "engagement_rate": aggregated.get("avg_engagement_rate", 0),
                    "influence_score": latest_score.score if latest_score else 0.0,
                },
                "platform_breakdown": [
                    {
                        "platform":       t.platform_name,
                        "username":       t.platform_username,
                        "is_active":      t.is_active,
                        "last_synced_at": t.last_synced_at.isoformat() if t.last_synced_at else None,
                        "needs_sync":     t.last_synced_at is None,
                    }
                    for t in platforms
                ],
                "trend": trend,
            },
        }

    def update_profile(
        self,
        user_id: UUID,
        bio: str | None = None,
        category: str | None = None,
        is_public: bool | None = None,
    ) -> dict[str, Any]:
        """Update editable fields on the creator's profile."""
        profile_repo = SQLCreatorProfileRepository(self.session)
        profile = profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Creator profile not found. Connect a platform first.")

        if bio       is not None: profile.bio       = bio        # type: ignore[assignment]
        if category  is not None: profile.category  = category   # type: ignore[assignment]
        if is_public is not None: profile.is_public = is_public  # type: ignore[assignment]
        self.session.commit()
        self.session.refresh(profile)

        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": {
                "creator_profile_id": str(profile.id),
                "bio":       profile.bio,
                "category":  profile.category,
                "is_public": profile.is_public,
            },
        }

    def list_content(self, creator_id: UUID) -> dict[str, Any]:
        profile_repo = SQLCreatorProfileRepository(self.session)
        profile      = profile_repo.get_by_user_id(creator_id)
        profile_id   = profile.id if profile else creator_id

        content_items = SQLContentRepository(self.session).get_by_creator(profile_id, limit=50, offset=0)
        items = [
            {
                "id":               str(c.id),
                "platform":         c.platform,
                "external_id":      c.external_id,
                "title":            c.title or c.caption,
                "permalink":        c.permalink,
                "thumbnail_url":    c.thumbnail_url,
                "duration_seconds": c.duration_seconds,
                "posted_at":        isoformat(c.posted_at) if c.posted_at else None,
                "synced_at":        isoformat(c.synced_at) if c.synced_at else None,
            }
            for c in content_items
        ]
        page = paginate_items(items, page=1, limit=50)
        return {
            "success": True,
            "message": "Creator content retrieved",
            "data": {"creator_id": str(creator_id), "items": page.items, "meta": asdict(page.meta)},
        }

    def get_audience(self, creator_id: UUID) -> dict[str, Any]:
        profile_repo = SQLCreatorProfileRepository(self.session)
        profile      = profile_repo.get_by_user_id(creator_id)
        profile_id   = profile.id if profile else creator_id

        snap     = SQLAudienceSnapshotRepository(self.session).latest_for_creator(profile_id)
        snap_dict = model_to_dict(snap) if snap else {}
        segments  = [asdict(s) for s in AudienceSegmenter().segment(snap_dict)] if snap_dict else []

        return {
            "success": True,
            "message": "Creator audience retrieved",
            "data": {
                "creator_id":              str(creator_id),
                "total_followers":         snap.total_followers            if snap else 0,
                "new_followers_this_period": snap.new_followers_this_period if snap else None,
                "age_distribution":        snap.age_distribution           if snap else {},
                "gender_distribution":     snap.gender_distribution        if snap else {},
                "top_countries":           snap.top_countries              if snap else [],
                "segments":                segments,
                "captured_at":             isoformat(snap.captured_at)     if snap and snap.captured_at else None,
            },
        }

    def list_platforms(self, creator_id: UUID) -> dict[str, Any]:
        platforms = SQLPlatformConnectionRepository(self.session).list_for_user(creator_id)
        return {
            "success": True,
            "message": "Creator platforms retrieved",
            "data": {
                "creator_id": str(creator_id),
                "items": [
                    {
                        "platform":         p.platform_name,
                        "username":         p.platform_username,
                        "platform_user_id": p.platform_user_id,
                        "is_active":        p.is_active,
                        "last_synced_at":   p.last_synced_at.isoformat() if p.last_synced_at else None,
                        "needs_sync":       p.last_synced_at is None,
                    }
                    for p in platforms
                ],
            },
        }

    def get_public_profile(self, creator_id: UUID) -> dict[str, Any]:
        """Returns the public-facing profile of a creator (delegated to DiscoverService)."""
        from app.services.discover_service import DiscoverService
        return DiscoverService(self.session).get_creator_detail(creator_id)
