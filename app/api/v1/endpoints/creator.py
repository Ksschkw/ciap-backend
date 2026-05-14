from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Body

from app.dependencies import get_creator_service, get_discover_service, get_current_user
from app.services.creator_service import CreatorService
from app.services.discover_service import DiscoverService

router = APIRouter(prefix="/creator", tags=["creator"])


@router.get("/me", summary="My Public Creator Profile", response_description="The creator's own public profile as SMEs see it")
def my_public_profile(
    current_user: dict[str, str] = Depends(get_current_user),
    discover_service: DiscoverService = Depends(get_discover_service),
) -> dict[str, object]:
    """
    **Creator endpoint.** Returns the logged-in creator's public-facing profile —
    exactly how an SME would see them in the discovery portal.

    Includes:
    - Bio, niche/category, location, follower count
    - Current influence score and tier (Nano → Mega)
    - Connected platforms
    - Recent public content highlights
    - Audience demographics snapshot

    Use this to power the "My Profile Preview" section on the creator dashboard.
    This is different from `GET /auth/me` which returns internal user/auth data.
    """
    return discover_service.get_creator_detail(UUID(current_user["id"]))


@router.patch("/me", summary="Update My Creator Profile", response_description="Updated creator profile")
def update_my_profile(
    current_user: dict[str, str] = Depends(get_current_user),
    creator_service: CreatorService = Depends(get_creator_service),
    bio: str | None = Body(default=None, description="Short bio or description"),
    category: str | None = Body(default=None, description="Content niche/category (e.g. 'Tech', 'Fashion')"),
    is_public: bool | None = Body(default=None, description="Whether your profile is visible to SMEs"),
) -> dict[str, object]:
    """
    **Creator endpoint.** Update your creator profile fields.

    Updatable fields:
    - `bio` — short description shown to SMEs
    - `category` — your content niche (used for SME filtering)
    - `is_public` — toggle visibility in the SME discovery portal

    Location and follower count are automatically set from your connected platforms on sync.
    """
    return creator_service.update_profile(
        user_id=UUID(current_user["id"]),
        bio=bio,
        category=category,
        is_public=is_public,
    )


@router.get("/dashboard", summary="Creator Dashboard Overview", response_description="Aggregated dashboard stats and recent activity")
def dashboard(
    current_user: dict[str, str] = Depends(get_current_user),
    creator_service: CreatorService = Depends(get_creator_service),
) -> dict[str, object]:
    """
    **Creator endpoint.** Returns an aggregated overview for the creator dashboard home page.

    Use `GET /analytics/summary` for the full analytics breakdown — this endpoint
    is a lighter-weight summary meant for the top-of-page stats row.
    """
    return creator_service.get_dashboard(UUID(current_user["id"]))


@router.get("/content", summary="My Content Items", response_description="List of synced content items for this creator")
def content(
    current_user: dict[str, str] = Depends(get_current_user),
    creator_service: CreatorService = Depends(get_creator_service),
) -> dict[str, object]:
    """
    **Creator endpoint.** Returns all synced content items (videos, posts) for the logged-in creator.

    Data is served from our DB — content is populated by `POST /youtube/sync`.
    Each item includes title, thumbnail, permalink, platform, and publish date.
    For per-item metrics, use `GET /analytics/content/{content_id}`.
    """
    return creator_service.list_content(UUID(current_user["id"]))


@router.get("/audience", summary="My Audience Snapshot", response_description="Latest audience demographics for the creator")
def audience(
    current_user: dict[str, str] = Depends(get_current_user),
    creator_service: CreatorService = Depends(get_creator_service),
) -> dict[str, object]:
    """
    **Creator endpoint.** Returns the latest audience demographics snapshot.

    Includes (when available via OAuth sync):
    - Age group distribution
    - Gender breakdown
    - Top countries by views
    - New followers this period

    Demographics are populated from YouTube Analytics API during `POST /youtube/sync`.
    """
    return creator_service.get_audience(UUID(current_user["id"]))


@router.get("/platforms", summary="My Connected Platforms", response_description="List of platform connections and their sync status")
def platforms(
    current_user: dict[str, str] = Depends(get_current_user),
    creator_service: CreatorService = Depends(get_creator_service),
) -> dict[str, object]:
    """
    **Creator endpoint.** Lists all platform accounts connected by the logged-in creator.

    Each entry shows:
    - Platform name (e.g. YOUTUBE)
    - Platform username and channel ID
    - Connection status (active/inactive)
    - `last_synced_at` — when data was last pulled from this platform
    - `needs_sync` — true if never synced

    Connect new platforms via `GET /oauth/{platform}/connect`.
    Trigger a data refresh via `POST /youtube/sync`.
    """
    return creator_service.list_platforms(UUID(current_user["id"]))


@router.get("/profile/public/{creator_id}", summary="View Any Creator's Public Profile", response_description="Public profile for a specific creator (by user ID)")
def public_profile(
    creator_id: UUID,
    creator_service: CreatorService = Depends(get_creator_service),
) -> dict[str, object]:
    """
    **Public endpoint.** View the full public profile of any creator by their `user_id`.

    This is the same data visible to SMEs in the discovery portal.
    No authentication required.
    """
    return creator_service.get_public_profile(creator_id)
