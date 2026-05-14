from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from DATA.data_connections.repositories import SQLCampaignRepository, SQLSMEProfileRepository, SQLUserRepository
from app.services.discover_service import DiscoverService
from app.utils.serialization import models_to_dicts


@dataclass(slots=True)
class SmeService:
    session: Session

    def get_dashboard(self, owner_id: UUID | None = None) -> dict[str, Any]:
        if owner_id is None:
            return {
                "success": True,
                "message": "SME dashboard retrieved",
                "data": {"summary": {"active_campaigns": 0, "available_creators": 0, "recommended_budget": 0}, "recommended_creators": []},
            }

        user_repo = SQLUserRepository(self.session)
        profile_repo = SQLSMEProfileRepository(self.session)
        campaign_repo = SQLCampaignRepository(self.session)

        user = user_repo.get_by_id(owner_id)
        profile = profile_repo.get_by_user_id(owner_id)
        if user is None:
            raise NotFoundError("SME user not found")

        campaigns = campaign_repo.get_by_owner(owner_id, limit=1000, offset=0)
        discover_service = DiscoverService(session=self.session)
        creators = discover_service.list_creators(limit=3)
        active_campaigns = [campaign for campaign in campaigns if str(campaign.status).upper() in {"DRAFT", "ACTIVE", "PAUSED"}]
        return {
            "success": True,
            "message": "SME dashboard retrieved",
            "data": {
                "company": {
                    "user_id": user.id,
                    "company_name": profile.company_name if profile is not None else None,
                    "industry": profile.industry if profile is not None else None,
                },
                "summary": {
                    "active_campaigns": len(active_campaigns),
                    "available_creators": creators["data"]["meta"]["total_items"],
                    "recommended_budget": 2000000 if profile is None or profile.industry is not None else 1500000,
                },
                "campaigns": models_to_dicts(campaigns),
                "recommended_creators": creators["data"]["items"],
            },
        }
