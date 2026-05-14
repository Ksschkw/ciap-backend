from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.schemas import CampaignCreateRequest, CampaignUpdateRequest
from app.core.exceptions import NotFoundError
from DATA.models.campaigns import Campaign
from DATA.data_connections.repositories import (
    SQLCampaignRepository,
    SQLInfluenceScoreRepository,
    SQLContentMetricRepository,
)
from app.ml.campaign_forecaster import CampaignForecaster
from app.utils.pagination import paginate_items
from app.utils.serialization import model_to_dict, models_to_dicts


@dataclass(slots=True)
class CampaignService:
    session: Session

    def list_campaigns(self, owner_id: UUID | None = None, page: int = 1, limit: int = 20, status: str | None = None) -> dict[str, Any]:
        repository = SQLCampaignRepository(self.session)
        if owner_id is None:
            campaigns = repository.list(limit=1000, offset=0)
        else:
            campaigns = repository.get_by_owner(owner_id, limit=1000, offset=0)

        items = models_to_dicts(campaigns)
        if status is not None:
            normalized_status = status.lower()
            items = [item for item in items if str(item["status"]).lower() == normalized_status]
        page_result = paginate_items(items, page=page, limit=limit)
        return {"success": True, "message": "Campaigns retrieved", "data": {"items": page_result.items, "meta": asdict(page_result.meta)}}

    def create_campaign(self, owner_id: UUID | None, payload: CampaignCreateRequest) -> dict[str, Any]:
        if owner_id is None:
            raise NotFoundError("Campaign owner not provided")

        metric_repo = SQLContentMetricRepository(self.session)
        score_repo = SQLInfluenceScoreRepository(self.session)
        latest_metric = metric_repo.latest_for_user(owner_id)
        latest_score = score_repo.latest_for_creator(owner_id)
        metric_values = model_to_dict(latest_metric).get("metrics", {}) if latest_metric is not None else {}
        if latest_score is not None:
            metric_values = {**metric_values, "influence_score": latest_score.score}

        duration_days = 14
        if payload.start_date is not None and payload.end_date is not None:
            duration_days = max(1, (payload.end_date - payload.start_date).days + 1)
        forecast = CampaignForecaster().forecast(
            metric_values,
            budget=float(payload.budget or 2000000),
            duration_days=duration_days,
            goal=payload.goal or "awareness",
        )
        campaign = Campaign(
            sme_id=str(owner_id),
            name=payload.name,
            goal=payload.goal,
            budget=payload.budget,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status="DRAFT",
        )
        created_campaign = SQLCampaignRepository(self.session).add(campaign)
        return {
            "success": True,
            "message": "Campaign created successfully",
            "data": {
                **model_to_dict(created_campaign),
                "forecast": asdict(forecast),
                "creator_score": latest_score.score if latest_score is not None else 0.0,
            },
        }

    def get_campaign(self, campaign_id: UUID) -> dict[str, Any]:
        campaign = SQLCampaignRepository(self.session).get_by_id(campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")
        return {
            "success": True,
            "message": "Campaign detail retrieved",
            "data": {
                **model_to_dict(campaign),
                "collaborations": [],
            },
        }

    def update_campaign(self, campaign_id: UUID, payload: CampaignUpdateRequest, current_user_id: UUID) -> dict[str, Any]:
        from DATA.models.users import User, SMEProfile
        user = self.session.query(User).filter(User.id == current_user_id).first()
        is_admin = user and user.role == "ADMIN"
        
        repository = SQLCampaignRepository(self.session)
        campaign = repository.get_by_id(campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")

        sme_profile = self.session.query(SMEProfile).filter(SMEProfile.id == campaign.sme_id).first()
        is_owner = sme_profile and sme_profile.user_id == current_user_id
        
        if not (is_owner or is_admin):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized to update this campaign")

        if payload.name is not None:
            campaign.name = payload.name
        if payload.goal is not None:
            campaign.goal = payload.goal
        if payload.budget is not None:
            campaign.budget = payload.budget
        if payload.start_date is not None:
            campaign.start_date = payload.start_date
        if payload.end_date is not None:
            campaign.end_date = payload.end_date
        if payload.status is not None:
            campaign.status = payload.status

        self.session.flush()
        return {
            "success": True,
            "message": "Campaign updated successfully",
            "data": {
                **model_to_dict(campaign),
            },
        }

    def delete_campaign(self, campaign_id: UUID, current_user_id: UUID) -> dict[str, Any]:
        from DATA.models.users import User, SMEProfile
        user = self.session.query(User).filter(User.id == current_user_id).first()
        is_admin = user and user.role == "ADMIN"
        
        repository = SQLCampaignRepository(self.session)
        campaign = repository.get_by_id(campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")
            
        sme_profile = self.session.query(SMEProfile).filter(SMEProfile.id == campaign.sme_id).first()
        is_owner = sme_profile and sme_profile.user_id == current_user_id
        
        if not (is_owner or is_admin):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized to delete this campaign")
            
        repository.delete(campaign_id)
        return {"success": True, "message": "Campaign deleted successfully", "data": {"id": str(campaign_id)}}

    def invite_creator(self, campaign_id: UUID, creator_id: UUID, current_user_id: UUID) -> dict[str, Any]:
        from DATA.models.campaigns import CampaignCollaboration, Campaign
        from DATA.models.users import CreatorProfile
        from app.services.notification_service import NotificationService
        
        campaign = self.session.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise NotFoundError("Campaign not found")
            
        creator = self.session.query(CreatorProfile).filter(CreatorProfile.id == creator_id).first()
        if not creator:
            raise NotFoundError("Creator not found")
            
        existing = self.session.query(CampaignCollaboration).filter(
            CampaignCollaboration.campaign_id == campaign_id,
            CampaignCollaboration.creator_id == creator_id
        ).first()
        
        if existing:
            return {"success": False, "message": "Creator is already invited to this campaign", "data": {}}
            
        import uuid
        collab = CampaignCollaboration(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            creator_id=creator_id,
            status="INVITED"
        )
        self.session.add(collab)
        
        # Send notification to creator
        notification_service = NotificationService(self.session)
        notification_service.create_notification(
            user_id=creator.user_id,
            title="New Campaign Invitation",
            body=f"You have been invited to collaborate on the campaign '{campaign.name}'.",
            notification_type="CAMPAIGN_INVITE",
            related_entity_id=collab.id
        )
        
        self.session.commit()
        return {"success": True, "message": "Creator invited successfully", "data": {"collaboration_id": str(collab.id)}}
