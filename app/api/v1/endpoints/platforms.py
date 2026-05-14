from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.schemas import PlatformSyncRequest
from app.dependencies import get_current_user
from app.dependencies import get_platform_service
from app.services.platform_service import PlatformService

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("")
def list_platforms(
    current_user: dict[str, str] = Depends(get_current_user),
    platform_service: PlatformService = Depends(get_platform_service),
) -> dict[str, object]:
    return platform_service.list_platforms(UUID(current_user["id"]))


@router.post("/sync")
def sync_platforms(
    payload: PlatformSyncRequest | None = None,
    current_user: dict[str, str] = Depends(get_current_user),
    platform_service: PlatformService = Depends(get_platform_service),
) -> dict[str, object]:
    return platform_service.sync_platforms(payload, UUID(current_user["id"]))
