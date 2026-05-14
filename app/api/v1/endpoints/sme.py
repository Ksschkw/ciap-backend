from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Body, Query

from app.dependencies import get_sme_service, get_discover_service, get_current_user
from app.services.sme_service import SmeService
from app.services.discover_service import DiscoverService

router = APIRouter(prefix="/sme", tags=["sme"])


@router.get("/dashboard", summary="SME Dashboard Overview", response_description="Key stats and recent activity for the SME")
def dashboard(
    current_user: dict[str, str] = Depends(get_current_user),
    sme_service: SmeService = Depends(get_sme_service),
) -> dict[str, object]:
    """
    **SME/Agency endpoint.** Returns a high-level overview for the SME dashboard home.

    Includes:
    - Active campaign count and total budget
    - Recent campaign activity
    - Top-performing creators from their shortlist

    Use this to populate the SME dashboard landing page.
    """
    return sme_service.get_dashboard(UUID(current_user["id"]))


@router.get("/discover", summary="Discover Creators (SME)", response_description="Filtered, ranked list of creators")
def discover(
    query: str | None = Query(default=None, description="Search by name or niche"),
    niche: str | None = Query(default=None, description="Filter by content niche/category"),
    location: str | None = Query(default=None, description="Filter by country code (e.g. 'NG')"),
    platform: str | None = Query(default=None, description="Filter by platform (e.g. 'youtube')"),
    min_followers: int | None = Query(default=None, ge=0),
    max_followers: int | None = Query(default=None, ge=0),
    min_score: float | None = Query(default=None, ge=0, le=100),
    max_score: float | None = Query(default=None, ge=0, le=100),
    sort_by: str = Query(default="influence_score", description="Sort by: influence_score | total_followers | engagement_rate"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME/Agency endpoint.** Search and filter creators in the CIAP database.

    All data is served from our DB (never calls YouTube directly).
    Use `sort_by=influence_score` (default) for best-performing first.

    **Combine filters** for precision targeting:
    - `niche=fashion&location=NG&min_score=30` → Nigerian fashion creators with score ≥ 30
    - `platform=youtube&min_followers=10000` → YouTube creators with 10k+ subscribers
    """
    return discover_service.list_creators(
        query=query, niche=niche, location=location, platform=platform,
        min_followers=min_followers, max_followers=max_followers,
        min_score=min_score, max_score=max_score,
        sort_by=sort_by, page=page, limit=limit,
    )


@router.get("/rankings", summary="Creator Leaderboard (SME view)", response_description="Top creators ranked by score or followers")
def rankings(
    sort_by: str = Query(default="influence_score"),
    niche: str | None = Query(default=None),
    location: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME/Agency endpoint.** Returns a ranked leaderboard of creators.

    Default: sorted by `influence_score` descending.
    Optionally filter by niche or location to see ranked creators within a category.

    Use this to power the "Top Creators" section on the SME portal.
    """
    return discover_service.list_creators(sort_by=sort_by, niche=niche, location=location, page=page, limit=limit)


@router.get("/creators/{creator_id}", summary="Creator Profile (SME Detail View)", response_description="Full public profile of a creator")
def creator_detail(
    creator_id: UUID,
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME/Agency endpoint.** View the full public profile of a specific creator.

    Returns bio, niche, location, platform stats, influence score, audience demographics,
    and their most recent public content items.

    Use this when an SME clicks on a creator card to drill into their profile.
    """
    return discover_service.get_creator_detail(creator_id)


@router.post("/compare", summary="Compare Creators Side-by-Side", response_description="Ranked comparison of selected or top creators")
def compare(
    creator_ids: List[UUID] = Body(default=[], description="List of creator UUIDs to compare. Leave empty to get the global top-10."),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **SME/Agency endpoint.** Returns a side-by-side ranked comparison of creators.

    Pass a JSON array of creator UUIDs in the body to compare a specific shortlist.
    Leave the body empty (`[]`) to get the top-10 by influence score.

    Results include real engagement rate, influence score, and audience fit metrics
    read directly from the database — no estimates or hardcoded values.
    """
    return discover_service.compare_creators(creator_ids=creator_ids or None)
