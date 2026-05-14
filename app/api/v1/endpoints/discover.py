from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query

from app.dependencies import get_discover_service, get_current_user
from app.services.discover_service import DiscoverService

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("/creators", summary="Search & Discover Creators", response_description="Paginated list of creators matching the filters")
def list_creators(
    query: str | None = Query(default=None, description="Search by name, niche, or keywords"),
    niche: str | None = Query(default=None, description="Filter by content niche/category (e.g., 'fashion', 'tech')"),
    location: str | None = Query(default=None, description="Filter by creator location country code (e.g., 'NG')"),
    platform: str | None = Query(default=None, description="Filter by connected platform (e.g., 'youtube')"),
    min_followers: int | None = Query(default=None, ge=0, description="Minimum total follower count"),
    max_followers: int | None = Query(default=None, ge=0, description="Maximum total follower count"),
    min_score: float | None = Query(default=None, ge=0, description="Minimum influence score (0–100)"),
    max_score: float | None = Query(default=None, ge=0, description="Maximum influence score (0–100)"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME endpoint.** Search through all creators in our database.

    This NEVER calls YouTube — it only queries our internal DB, protecting API quotas.
    Creators are populated via `POST /youtube/ingest-public` (admin background job).

    **Filtering options:**
    - Filter by niche, location, platform, follower range, or score range
    - Combine multiple filters for precision targeting

    **Sorting:** Results are always ordered by `influence_score` descending by default.
    Use the `/discover/rankings` endpoint for explicit sorted leaderboards.
    """
    return discover_service.list_creators(
        query=query,
        niche=niche,
        location=location,
        platform=platform,
        min_followers=min_followers,
        max_followers=max_followers,
        min_score=min_score,
        max_score=max_score,
        page=page,
        limit=limit,
    )


@router.get("/rankings", summary="Creator Leaderboard / Rankings", response_description="Sorted list of creators by influence score or specified metric")
def creator_rankings(
    sort_by: str = Query(default="influence_score", description="Sort field: influence_score | total_followers | engagement_rate"),
    niche: str | None = Query(default=None, description="Filter rankings to a specific content niche"),
    location: str | None = Query(default=None, description="Filter rankings to a specific country code"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME endpoint.** Returns a ranked leaderboard of creators on the platform.

    Default sort is by `influence_score` descending (highest performer first).

    Supports sorting by:
    - `influence_score` — overall platform score (recommended)
    - `total_followers` — pure subscriber/follower count
    - `engagement_rate` — avg engagement regardless of size

    Use this to power the "Top Creators" discovery section on the SME dashboard.
    """
    return discover_service.list_creators(
        sort_by=sort_by,
        niche=niche,
        location=location,
        page=page,
        limit=limit,
    )


@router.get("/creators/{creator_id}", summary="Creator Profile Detail", response_description="Complete public profile of a single creator including score and recent content")
def creator_detail(
    creator_id: UUID,
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME endpoint.** View the full public profile of a specific creator.

    Returns:
    - Bio, niche, location, connected platforms
    - Current influence score and tier (Nano / Micro / Mid-Tier / Macro / Mega)
    - Recent public content items with metrics
    - Audience demographics snapshot

    Use this when an SME clicks on a creator's card to see their detailed profile.
    """
    return discover_service.get_creator_detail(creator_id)


@router.post("/compare", summary="Compare Multiple Creators", response_description="Side-by-side metric comparison for a list of creator IDs")
def compare_creators(
    creator_ids: List[UUID] = Body(default=[], description="List of creator UUIDs to compare. Leave empty to get the global top-10."),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME endpoint.** Compare multiple creators side by side.

    Pass a JSON array of creator UUIDs in the request body and receive a
    structured, ranked comparison of their key metrics — followers, real
    engagement rate, influence score — in a single response.

    Leave the body empty (`[]`) to get the global top-10 by influence score.

    Example body:
    ```json
    ["uuid-1", "uuid-2", "uuid-3"]
    ```
    """
    return discover_service.compare_creators(creator_ids=creator_ids or None)
