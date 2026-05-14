from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from DATA.data_connections.repositories import (
    SQLCampaignRepository,
    SQLCreatorProfileRepository,
    SQLPlatformConnectionRepository,
    SQLInfluenceScoreRepository,
    SQLUserRepository,
)
from app.utils.serialization import models_to_dicts


@dataclass(slots=True)
class AdminService:
    session: Session

    def get_dashboard(self) -> dict[str, Any]:
        user_repo = SQLUserRepository(self.session)
        creator_repo = SQLCreatorProfileRepository(self.session)
        campaign_repo = SQLCampaignRepository(self.session)
        platform_repo = SQLPlatformConnectionRepository(self.session)
        score_repo = SQLInfluenceScoreRepository(self.session)

        users_total = user_repo.count()
        creators_total = creator_repo.count()
        campaigns_total = campaign_repo.count()
        platform_tokens_total = platform_repo.count()
        scores_total = score_repo.count()

        return {
            "success": True,
            "message": "Admin dashboard retrieved",
            "data": {
                "summary": {
                    "users_total": users_total,
                    "creators_total": creators_total,
                    "campaigns_total": campaigns_total,
                    "platform_tokens_total": platform_tokens_total,
                    "scores_total": scores_total,
                }
            },
        }

    def list_users(self) -> dict[str, Any]:
        users = SQLUserRepository(self.session).list(limit=100, offset=0)
        return {"success": True, "message": "Users retrieved", "data": {"items": models_to_dicts(users)}}

    def get_platform_health(self) -> dict[str, Any]:
        platforms = SQLPlatformConnectionRepository(self.session).list(limit=100, offset=0)
        connected = [platform for platform in platforms if platform.is_active]
        by_platform: dict[str, int] = {}
        for platform in platforms:
            by_platform[platform.platform_name] = by_platform.get(platform.platform_name, 0) + 1

        return {
            "success": True,
            "message": "Platform health retrieved",
            "data": {
                "connected_accounts": len(connected),
                "inactive_accounts": len(platforms) - len(connected),
                "by_platform": by_platform,
            },
        }
