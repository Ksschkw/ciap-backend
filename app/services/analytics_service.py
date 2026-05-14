from __future__ import annotations

from dataclasses import dataclass
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
    SQLUserRepository,
    SQLPlatformConnectionRepository,
)
from app.ml.influence_scorer import InfluenceScorer
from app.utils.date_utils import isoformat
from app.utils.serialization import model_to_dict, models_to_dicts


@dataclass(slots=True)
class AnalyticsService:
    session: Session

    def summary(self, creator_id: UUID | None = None) -> dict[str, Any]:
        """
        Return a comprehensive analytics snapshot for a creator.
        All data is served from our database — never calls YouTube directly.
        """
        if creator_id is None:
            return {
                "success": True,
                "message": "Analytics summary retrieved",
                "data": {
                    "followers": 0, "views": 0, "engagement_rate": 0.0,
                    "growth_rate": 0.0, "content_count": 0, "influence_score": 0.0,
                    "platform_breakdown": [], "audience": {}, "top_content": [],
                },
            }

        user_repo    = SQLUserRepository(self.session)
        profile_repo = SQLCreatorProfileRepository(self.session)
        content_repo = SQLContentRepository(self.session)
        metric_repo  = SQLContentMetricRepository(self.session)
        audience_repo = SQLAudienceSnapshotRepository(self.session)
        score_repo   = SQLInfluenceScoreRepository(self.session)
        platform_repo = SQLPlatformConnectionRepository(self.session)

        user    = user_repo.get_by_id(creator_id)
        profile = profile_repo.get_by_user_id(creator_id)
        if user is None:
            raise NotFoundError("Creator not found")

        # ── CRITICAL: ContentItem.creator_id → creator_profiles.id, NOT users.id
        # All content/metric queries must use profile.id, not creator_id (user.id)
        profile_id = profile.id if profile else creator_id

        # ── Core metrics ──────────────────────────────────────────────────────
        aggregated       = metric_repo.get_aggregated_for_creator(profile_id)
        recent_snapshots = metric_repo.list_for_user(profile_id, limit=12, offset=0)
        latest_audience  = audience_repo.latest_for_creator(profile_id)
        latest_score     = score_repo.latest_for_creator(creator_id)
        score_history    = score_repo.get_history_for_creator(creator_id, limit=12)
        content_items    = content_repo.get_by_creator(profile_id, limit=5, offset=0)
        platforms        = platform_repo.list_for_user(creator_id)

        # ── Growth rate: compare newest vs oldest snapshot in series ──────────
        if len(recent_snapshots) > 1:
            newest_views = int(recent_snapshots[0].views or 0)
            oldest_views = int(recent_snapshots[-1].views or 0)
            growth_rate = round((newest_views - oldest_views) / max(oldest_views, 1), 4)
        else:
            growth_rate = 0.0

        # ── Influence score: stored or freshly computed ───────────────────────
        audience_data = model_to_dict(latest_audience) if latest_audience else {}
        if latest_score is not None:
            influence_score = round(float(latest_score.score), 4)
            score_breakdown = latest_score.breakdown if hasattr(latest_score, "breakdown") else {}
        else:
            scored = InfluenceScorer().score(aggregated, audience_data)
            influence_score = round(float(scored.score), 4)
            score_breakdown = {}

        # ── Score history for charts ──────────────────────────────────────────
        score_trend = [
            {"date": isoformat(s.scored_at), "score": round(float(s.score), 4)}
            for s in reversed(score_history)
        ]

        # ── Platform breakdown ────────────────────────────────────────────────
        platform_breakdown = [
            {
                "platform": p.platform_name,
                "is_active": p.is_active,
                "last_synced_at": isoformat(p.last_synced_at) if p.last_synced_at else None,
            }
            for p in platforms
        ]

        # ── Top content (most recent synced videos) ───────────────────────────
        top_content = []
        for item in content_items:
            latest_item_metric = metric_repo.get_latest_for_content(item.id)
            top_content.append({
                "id": str(item.id),
                "title": item.title or item.caption or item.external_id,
                "platform": item.platform,
                "permalink": item.permalink,
                "thumbnail_url": item.thumbnail_url,
                "posted_at": isoformat(item.posted_at) if item.posted_at else None,
                "views":    int(latest_item_metric.views    or 0) if latest_item_metric else 0,
                "likes":    int(latest_item_metric.likes    or 0) if latest_item_metric else 0,
                "comments": int(latest_item_metric.comments or 0) if latest_item_metric else 0,
                "duration_seconds": item.duration_seconds,
            })

        # ── Audience demographics ─────────────────────────────────────────────
        audience_payload = {}
        if latest_audience:
            a = model_to_dict(latest_audience)
            audience_payload = {
                "total_subscribers": a.get("total_followers") or a.get("total_subscribers") or 0,
                "demographics":      a.get("demographics", {}),
                "top_countries":     a.get("top_countries", []),
                "captured_at":       isoformat(latest_audience.captured_at) if latest_audience.captured_at else None,
            }

        return {
            "success": True,
            "message": "Analytics summary retrieved",
            "data": {
                "creator_id":       str(user.id),
                "full_name":        user.full_name or user.email,
                "avatar_url":       user.avatar_url,
                # ── Core KPIs ──
                "total_followers":  profile.total_followers if profile and profile.total_followers else 0,
                "total_views":      aggregated["total_views"],
                "total_likes":      aggregated["total_likes"],
                "total_comments":   aggregated["total_comments"],
                "total_shares":     aggregated["total_shares"],
                "engagement_rate":  aggregated["avg_engagement_rate"],
                "growth_rate":      growth_rate,
                "content_count":    len(content_items),
                # ── Score ──
                "influence_score":  influence_score,
                "score_breakdown":  score_breakdown,
                "score_trend":      score_trend,
                # ── Context ──
                "platform_breakdown": platform_breakdown,
                "audience":         audience_payload,
                "top_content":      top_content,
            },
        }

    def trends(self, creator_id: UUID | None = None) -> dict[str, Any]:
        """Return time-series data for the creator's views AND engagement rate — for chart rendering."""
        if creator_id is None:
            return {
                "success": True,
                "message": "Analytics trends retrieved",
                "data": {"views_series": [], "engagement_series": [], "score_series": []},
            }

        metric_repo = SQLContentMetricRepository(self.session)
        score_repo  = SQLInfluenceScoreRepository(self.session)
        profile_repo = SQLCreatorProfileRepository(self.session)

        profile  = profile_repo.get_by_user_id(creator_id)
        profile_id = profile.id if profile else creator_id

        snapshots     = metric_repo.list_for_user(profile_id, limit=30, offset=0)
        score_history = score_repo.get_history_for_creator(creator_id, limit=30)

        views_series = [
            {
                "date":  isoformat(s.captured_at),
                "value": int(s.views or 0),
            }
            for s in reversed(snapshots)
        ]
        engagement_series = [
            {
                "date":  isoformat(s.captured_at),
                "value": round(int(s.likes or 0) / max(int(s.views or 1), 1), 4),
            }
            for s in reversed(snapshots)
        ]
        score_series = [
            {"date": isoformat(s.scored_at), "value": round(float(s.score), 4)}
            for s in reversed(score_history)
        ]

        return {
            "success": True,
            "message": "Analytics trends retrieved",
            "data": {
                "views_series":      views_series,
                "engagement_series": engagement_series,
                "score_series":      score_series,
            },
        }

    def content_detail(self, content_id: UUID, current_creator_id: UUID | None = None) -> dict[str, Any]:
        """Return deep analytics for a single content item."""
        content_repo = SQLContentRepository(self.session)
        metric_repo  = SQLContentMetricRepository(self.session)

        content = content_repo.get_by_id(content_id)
        if content is None:
            raise NotFoundError("Content not found")

        # Get the full metric history for this content item (for sparklines)
        latest_metric  = metric_repo.get_latest_for_content(content_id)
        metric_history = metric_repo.get_history(content_id, limit=10)

        metrics_payload = {
            "views":    int(latest_metric.views    or 0),
            "likes":    int(latest_metric.likes    or 0),
            "comments": int(latest_metric.comments or 0),
            "shares":   int(latest_metric.shares   or 0),
        } if latest_metric else {}
        history_series = [
            {
                "date":     isoformat(m.captured_at),
                "views":    int(m.views    or 0),
                "likes":    int(m.likes    or 0),
                "comments": int(m.comments or 0),
            }
            for m in reversed(metric_history)
        ]

        # content.creator_id is already creator_profiles.id — use it directly
        avg_views = avg_likes = 0
        if content.creator_id:
            agg = metric_repo.get_aggregated_for_creator(content.creator_id)
            creator_content_count = len(content_repo.get_by_creator(content.creator_id, limit=1000))
            avg_views = agg["total_views"] // max(creator_content_count, 1)
            avg_likes = agg["total_likes"] // max(creator_content_count, 1)

        item_views = int(metrics_payload.get("views", 0) or 0)
        item_likes = int(metrics_payload.get("likes", 0) or 0)

        return {
            "success": True,
            "message": "Content detail retrieved",
            "data": {
                "id":            str(content.id),
                "platform":      content.platform,
                "creator_id":    str(content.creator_id),
                "external_id":   content.external_id,
                "media_type":    content.media_type,
                "title":         content.title or content.caption,
                "permalink":     content.permalink,
                "thumbnail_url": content.thumbnail_url,
                "posted_at":     isoformat(content.posted_at) if content.posted_at else None,
                "synced_at":     isoformat(content.synced_at) if content.synced_at else None,
                # ── Current metrics ──
                "metrics": {
                    "views":           item_views,
                    "likes":           item_likes,
                    "comments":        int(metrics_payload.get("comments", 0) or 0),
                    "shares":          int(metrics_payload.get("shares", 0) or 0),
                    "engagement_rate": round(item_likes / max(item_views, 1), 4),
                    "captured_at":     isoformat(latest_metric.captured_at) if latest_metric else None,
                },
                # ── Relative to creator average ──
                "vs_creator_avg": {
                    "views_delta": item_views - avg_views,
                    "likes_delta": item_likes - avg_likes,
                    "above_average_views": item_views > avg_views,
                },
                # ── Historical spark-line ──
                "history": history_series,
            },
        }

    def influence_score(self, creator_id: UUID) -> dict[str, Any]:
        """Return the current influence score, score history and full metric breakdown."""
        score_repo    = SQLInfluenceScoreRepository(self.session)
        metric_repo   = SQLContentMetricRepository(self.session)
        audience_repo = SQLAudienceSnapshotRepository(self.session)
        profile_repo  = SQLCreatorProfileRepository(self.session)

        profile    = profile_repo.get_by_user_id(creator_id)
        profile_id = profile.id if profile else creator_id

        latest_score    = score_repo.latest_for_creator(creator_id)
        score_history   = score_repo.get_history_for_creator(creator_id, limit=52)
        aggregated      = metric_repo.get_aggregated_for_creator(profile_id)
        latest_audience = audience_repo.latest_for_creator(profile_id)

        # Compute live if never scored before
        if latest_score is None:
            audience_data = model_to_dict(latest_audience) if latest_audience else {}
            computed = InfluenceScorer().score(aggregated, audience_data)
            score_val   = round(float(computed.score), 4)
            tier        = _score_to_tier(score_val)
        else:
            score_val = round(float(latest_score.score), 4)
            tier      = _score_to_tier(score_val)

        history = [
            {"date": isoformat(s.scored_at), "score": round(float(s.score), 4)}
            for s in reversed(score_history)
        ]

        return {
            "success": True,
            "message": "Influence score retrieved",
            "data": {
                "creator_id":      str(creator_id),
                "score":           score_val,
                "tier":            tier,
                "total_followers": profile.total_followers if profile else 0,
                "metrics": {
                    "total_views":       aggregated["total_views"],
                    "total_likes":       aggregated["total_likes"],
                    "total_comments":    aggregated["total_comments"],
                    "avg_engagement_rate": aggregated["avg_engagement_rate"],
                },
                "last_scored_at": isoformat(latest_score.scored_at) if latest_score else None,
                "history":         history,
            },
        }


def _score_to_tier(score: float) -> str:
    """Convert a numeric influence score to a readable creator tier."""
    if score >= 80:
        return "Mega"
    if score >= 60:
        return "Macro"
    if score >= 40:
        return "Mid-Tier"
    if score >= 20:
        return "Micro"
    return "Nano"
