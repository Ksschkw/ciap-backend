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


@router.put("/{campaign_id}", summary="Update Campaign", response_description="Updated campaign data")
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdateRequest,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    """
    Update an existing campaign's details.
    
    The frontend should provide only the fields that are being changed. 
    Only the campaign owner (SME) can modify the campaign details.
    """
    return campaign_service.update_campaign(campaign_id, payload, UUID(current_user["id"]))


@router.delete("/{campaign_id}", summary="Delete Campaign", response_description="Success status")
def delete_campaign(
    campaign_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    """
    Delete a specific campaign by its ID.
    
    This will permanently remove the campaign and cancel any pending invitations.
    Only the campaign owner can delete it.
    """
    return campaign_service.delete_campaign(campaign_id, UUID(current_user["id"]))


@router.post("/{campaign_id}/invite/{creator_id}", status_code=status.HTTP_201_CREATED, summary="Invite Creator to Campaign", response_description="Collaboration object")
def invite_creator(
    campaign_id: UUID,
    creator_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, object]:
    """
    Invite a creator to participate in a campaign.
    
    This creates a new collaboration request. The creator will be notified and can
    then accept or decline the invitation.
    """
    # This assumes we implement invite_creator in CampaignService
    return campaign_service.invite_creator(campaign_id, creator_id, UUID(current_user["id"]))
