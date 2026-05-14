from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.schemas import CampaignCreateRequest, CampaignUpdateRequest
from app.dependencies import get_campaign_service
from app.dependencies import get_current_user
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", summary="List Campaigns", response_description="List of campaigns matching criteria")
def list_campaigns(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    """
    Retrieve a paginated list of campaigns for the authenticated SME.
    
    Can be filtered by `status` (e.g., DRAFT, ACTIVE, COMPLETED).
    """
    return campaign_service.list_campaigns(owner_id=UUID(current_user["id"]), page=page, limit=limit, status=status)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a Campaign", response_description="Details of the newly created campaign including forecasted reach")
def create_campaign(
    payload: CampaignCreateRequest,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    """
    Create a new campaign draft.
    
    Automatically generates a performance forecast based on the budget, duration,
    and the creator's current influence score metrics.
    """
    return campaign_service.create_campaign(UUID(current_user["id"]), payload)


@router.get("/{campaign_id}", summary="Get Campaign Details", response_description="Full campaign data and existing collaborations")
def campaign_detail(
    campaign_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    """
    Fetch the complete details of a specific campaign by its ID.
    """
    return campaign_service.get_campaign(campaign_id)


@router.put("/{campaign_id}")
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdateRequest,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    return campaign_service.update_campaign(campaign_id, payload, UUID(current_user["id"]))


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    return campaign_service.delete_campaign(campaign_id, UUID(current_user["id"]))


@router.post("/{campaign_id}/invite/{creator_id}", status_code=status.HTTP_201_CREATED)
def invite_creator(
    campaign_id: UUID,
    creator_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    # This assumes we implement invite_creator in CampaignService
    return campaign_service.invite_creator(campaign_id, creator_id, UUID(current_user["id"]))
