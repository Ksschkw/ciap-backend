from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.schemas import PlatformSyncRequest
from app.dependencies import get_current_user
from app.dependencies import get_platform_service
from app.services.platform_service import PlatformService

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("", summary="List Connected Platforms", response_description="List of user's connected platforms")
def list_platforms(
    current_user: dict[str, str] = Depends(get_current_user),
    platform_service: PlatformService = Depends(get_platform_service),
) -> dict[str, object]:
    """
    Retrieve all external platform connections (like YouTube) for the authenticated user.
    
    Shows connection status and basic platform account details.
    """
    return platform_service.list_platforms(UUID(current_user["id"]))


@router.post("/sync", summary="Sync Platform Data", response_description="Sync job status")
def sync_platforms(
    payload: PlatformSyncRequest | None = None,
    current_user: dict[str, str] = Depends(get_current_user),
    platform_service: PlatformService = Depends(get_platform_service),
) -> dict[str, object]:
    """
    Trigger a manual sync to fetch the latest analytics and data from connected platforms.
    
    If no payload is provided, all connected platforms will be synced.
    Otherwise, specify the target platforms in the request body.
    """
    return platform_service.sync_platforms(payload, UUID(current_user["id"]))
