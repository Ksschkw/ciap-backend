from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from DATA.data_connections.repositories import (
    SQLAudienceSnapshotRepository,
    SQLContentRepository,
    SQLCreatorProfileRepository,
    SQLInfluenceScoreRepository,
    SQLPlatformConnectionRepository,
    SQLUserRepository,
)
from app.ml.audience_segmenter import AudienceSegmenter
from app.ml.influence_scorer import InfluenceScorer
from app.utils.serialization import model_to_dict, models_to_dicts


@dataclass(slots=True)
class DiscoverService:
    session: Session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _location_str(self, profile: Any) -> str | None:
        """Build a human-readable location string from the profile's columns."""
        city = getattr(profile, "location_city", None)
        country = getattr(profile, "location_country", None)
        legacy = getattr(profile, "location", None)
        if city and country:
            return f"{city}, {country}"
        return city or country or legacy or None

    def _profile_to_dict(self, profile: Any, score_repo: SQLInfluenceScoreRepository, token_repo: SQLPlatformConnectionRepository) -> dict[str, Any]:
        """
        Serialize a single CreatorProfile (with its pre-joined User attached as
        _cached_user) into a flat catalog dict.
        Uses the real influence_score and avg_engagement_rate columns — no fake math.
        """
        # User was joined and cached by search_creators()
        user = getattr(profile, "_cached_user", None)
        if user is None:
            user_repo = SQLUserRepository(self.session)
            user = user_repo.get_by_id(profile.user_id)
        if user is None:
            return {}

        followers = int(getattr(profile, "total_followers", None) or getattr(profile, "followers", None) or 0)
        social = getattr(profile, "social_handles", None) or getattr(profile, "social_links", None) or {}

        # Prefer the scored influence_score row; fall back to profile column
        score_row = score_repo.latest_for_creator(profile.user_id)
        influence_score = float(score_row.score if score_row is not None else (profile.influence_score or 0.0))

        # Use the real avg_engagement_rate stored by the influence scorer
        avg_engagement_rate = float(getattr(profile, "avg_engagement_rate", None) or 0.0)

        tokens = token_repo.list_for_user(profile.user_id)
        platform_name: str | None = getattr(profile, "top_platform", None) or (tokens[0].platform_name if tokens else None)

        return {
            "id": str(user.id),
            "full_name": user.full_name or user.email,
            "category": profile.category,
            "location": self._location_str(profile),
            "language_preference": user.language_preference,
            "followers": followers,
            "influence_score": influence_score,
            "avg_engagement_rate": avg_engagement_rate,
            "is_public": profile.is_public,
            "top_platform": platform_name.upper() if platform_name is not None else None,
            "platform": platform_name.lower() if platform_name is not None else None,
            "social_links": social,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def list_creators(
        self,
        query: str | None = None,
        niche: str | None = None,
        location: str | None = None,
        platform: str | None = None,
        min_followers: int | None = None,
        max_followers: int | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        sort_by: str = "influence_score",
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        All filtering, sorting, and pagination is executed inside the database.
        No Python-loop scanning of every creator row.
        """
        creator_repo = SQLCreatorProfileRepository(self.session)
        score_repo = SQLInfluenceScoreRepository(self.session)
        token_repo = SQLPlatformConnectionRepository(self.session)

        profiles, total_count = creator_repo.search_creators(
            query=query,
            niche=niche,
            location=location,
            platform=platform,
            min_followers=min_followers,
            max_followers=max_followers,
            min_score=min_score,
            max_score=max_score,
            sort_by=sort_by,
            page=page,
            limit=limit,
        )

        items = [
            d for d in
            (self._profile_to_dict(p, score_repo, token_repo) for p in profiles)
            if d  # drop any empty dicts (orphaned profiles with no user)
        ]

        total_pages = ceil(total_count / limit) if limit > 0 else 1
        return {
            "success": True,
            "message": "Creators discovered",
            "data": {
                "items": items,
                "meta": {
                    "page": page,
                    "limit": limit,
                    "total_items": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            },
        }

    def get_creator_detail(self, creator_id: UUID) -> dict[str, Any]:
        user_repo = SQLUserRepository(self.session)
        profile_repo = SQLCreatorProfileRepository(self.session)
        score_repo = SQLInfluenceScoreRepository(self.session)
        audience_repo = SQLAudienceSnapshotRepository(self.session)
        content_repo = SQLContentRepository(self.session)
        token_repo = SQLPlatformConnectionRepository(self.session)

        user = user_repo.get_by_id(creator_id)
        profile = profile_repo.get_by_user_id(creator_id)
        if user is None or profile is None:
            raise NotFoundError("Creator not found")

        followers = int(getattr(profile, "total_followers", None) or getattr(profile, "followers", None) or 0)
        social = getattr(profile, "social_handles", None) or getattr(profile, "social_links", None) or {}
        avg_engagement_rate = float(getattr(profile, "avg_engagement_rate", None) or 0.0)

        audience_snapshot = audience_repo.latest_for_creator(creator_id)
        audience_payload = model_to_dict(audience_snapshot) if audience_snapshot is not None else {}
        latest_score = score_repo.latest_for_creator(creator_id)
        if latest_score is None:
            score_result = InfluenceScorer().score(
                {"followers": followers, "content_count": 0, "influence_score": profile.influence_score or 0.0},
                audience_payload,
            )
            score_payload: dict[str, Any] = asdict(score_result)
        else:
            score_payload = model_to_dict(latest_score)

        segments = [asdict(segment) for segment in AudienceSegmenter().segment(audience_payload)] if audience_payload else []
        content_highlights = models_to_dicts(content_repo.get_by_creator(creator_id, limit=3, offset=0))
        platforms = token_repo.list_for_user(creator_id)

        return {
            "success": True,
            "message": "Creator detail retrieved",
            "data": {
                "id": str(creator_id),
                "full_name": user.full_name or user.email,
                "category": profile.category,
                "location": self._location_str(profile),
                "followers": followers,
                "avg_engagement_rate": avg_engagement_rate,
                "social_links": social,
                "bio": profile.bio,
                "platforms": [token.platform_name for token in platforms],
                "score": {
                    "current": score_payload.get("score", 0.0),
                    "model_version": score_payload.get("model_version"),
                },
                "audience": audience_payload,
                "content_highlights": content_highlights,
                "segments": segments,
            },
        }

    def compare_creators(self, creator_ids: list[UUID] | None = None) -> dict[str, Any]:
        """
        Return a side-by-side comparison of creators.

        If `creator_ids` is provided, only those creators are compared.
        Otherwise, falls back to the top 10 by influence_score (for the
        'full leaderboard compare' view on the SME dashboard).

        All metrics come directly from the database — no hardcoded multipliers.
        """
        creator_repo = SQLCreatorProfileRepository(self.session)
        user_repo = SQLUserRepository(self.session)
        score_repo = SQLInfluenceScoreRepository(self.session)
        token_repo = SQLPlatformConnectionRepository(self.session)

        if creator_ids:
            # Fetch only the requested profiles
            profiles = [creator_repo.get_by_user_id(cid) for cid in creator_ids]
            profiles = [p for p in profiles if p is not None and p.is_public]
        else:
            # Default: top 10 by influence_score from DB
            profiles, _ = creator_repo.search_creators(
                sort_by="influence_score",
                page=1,
                limit=10,
            )

        items: list[dict[str, Any]] = []
        for profile in profiles:
            user = getattr(profile, "_cached_user", None) or user_repo.get_by_id(profile.user_id)
            if user is None:
                continue

            followers = int(getattr(profile, "total_followers", None) or getattr(profile, "followers", None) or 0)
            social = getattr(profile, "social_handles", None) or getattr(profile, "social_links", None) or {}

            # Real influence score from scored row, fall back to profile column
            score_row = score_repo.latest_for_creator(profile.user_id)
            influence_score = float(score_row.score if score_row is not None else (profile.influence_score or 0.0))

            # Real engagement rate stored by influence scorer — not a flat 5%
            avg_engagement_rate = float(getattr(profile, "avg_engagement_rate", None) or 0.0)

            # Audience fit: how "macro" the creator is on a 0-1 scale (1 = 1M+ followers)
            audience_fit = round(min(followers / 1_000_000.0, 1.0), 4)

            tokens = token_repo.list_for_user(profile.user_id)
            platform_name: str | None = getattr(profile, "top_platform", None) or (tokens[0].platform_name if tokens else None)

            items.append({
                "creator_id": str(user.id),
                "full_name": user.full_name or user.email,
                "category": profile.category,
                "location": self._location_str(profile),
                "followers": followers,
                "influence_score": influence_score,
                "avg_engagement_rate": avg_engagement_rate,
                "audience_fit": audience_fit,
                "top_platform": platform_name.upper() if platform_name else None,
                "social_links": social,
            })

        # Sort by influence_score desc so highest-ranked appears first
        items.sort(key=lambda x: (x["influence_score"], x["followers"]), reverse=True)

        return {
            "success": True,
            "message": "Creator comparison generated",
            "data": {"items": items, "total": len(items)},
        }
