from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_analytics_service, get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", summary="Creator Analytics Summary", response_description="Full snapshot of metrics, audience, influence score, and top content")
def summary(
    current_user: dict[str, str] = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, object]:
    """
    **Primary creator dashboard endpoint.** Call this once on page load.

    Returns a complete snapshot including:
    - `total_followers`, `total_views`, `total_likes`, `engagement_rate`, `growth_rate`
    - `influence_score` + `score_breakdown` + `score_trend` (time-series for charts)
    - `platform_breakdown` — each connected platform and its sync status
    - `audience` — subscriber count and demographic data
    - `top_content` — the 5 most recently synced videos/posts with per-item metrics

    **DB-first:** All data is served from our database — YouTube API is NOT called here.
    To refresh data from YouTube, use `POST /youtube/sync`.
    """
    return analytics_service.summary(UUID(current_user["id"]))


@router.get("/trends", summary="Analytics Trends (Time-Series)", response_description="Time-series arrays for chart rendering")
def trends(
    current_user: dict[str, str] = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, object]:
    """
    Returns three separate time-series arrays — perfect for drawing charts:

    - `views_series` — daily/weekly view counts over time
    - `engagement_series` — engagement rate over time
    - `score_series` — influence score progression over time

    Each entry has `{"date": "ISO-8601", "value": number}`.
    """
    return analytics_service.trends(UUID(current_user["id"]))


@router.get("/score", summary="My Influence Score", response_description="Current score, creator tier, score history and raw metric breakdown")
def my_influence_score(
    current_user: dict[str, str] = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, object]:
    """
    Returns the authenticated creator's influence score in detail:

    - `score` — 0–100 numeric score
    - `tier` — human label: Nano / Micro / Mid-Tier / Macro / Mega
    - `metrics` — the raw totals that drove the score
    - `history` — up to 52 weekly score snapshots for sparkline charts

    Use this to power the "Your Score" card on the Creator Dashboard.
    """
    return analytics_service.influence_score(UUID(current_user["id"]))


@router.get("/content/{content_id}", summary="Content Item Deep Analytics", response_description="Detailed metrics for a single piece of content including vs-average comparison")
def content_detail(
    content_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, object]:
    """
    Deep analytics for a single piece of content (e.g., one YouTube video).

    Returns:
    - Current snapshot metrics (views, likes, comments, engagement rate)
    - `vs_creator_avg` — how this item compares to the creator's channel average
    - `history` — a 10-point time-series of this item's metrics over time

    Use this to power individual content drill-down pages.
    """
    return analytics_service.content_detail(content_id, UUID(current_user["id"]))
