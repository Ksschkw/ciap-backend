from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.schemas import PlatformSyncRequest
from DATA.data_connections.repositories import SQLPlatformConnectionRepository


@dataclass(slots=True)
class PlatformService:
    session: Session

    def list_platforms(self, user_id: UUID | None = None) -> dict[str, Any]:
        connected_platforms = [] if user_id is None else SQLPlatformConnectionRepository(self.session).list_for_user(user_id)
        return {
            "success": True,
            "message": "Platforms retrieved",
            "data": {
                "items": [
                    {
                        "platform": platform.platform_name,
                        "platform_user_id": platform.platform_user_id,
                        "is_active": platform.is_active,
                        "last_synced_at": platform.last_synced_at,
                    }
                    for platform in connected_platforms
                ],
            },
        }

    def sync_platforms(self, payload: PlatformSyncRequest | None = None, user_id: UUID | None = None) -> dict[str, Any]:
        connected_platforms = [] if user_id is None else SQLPlatformConnectionRepository(self.session).list_for_user(user_id)
        resolved_platforms = payload.platforms if payload is not None and payload.platforms is not None else [platform.platform_name for platform in connected_platforms]
        from app.tasks.sync_tasks import sync_platform_data

        task_result = sync_platform_data.delay(str(user_id) if user_id is not None else None, resolved_platforms)
        return {
            "success": True,
            "message": "Platform sync queued",
            "data": {
                "task_id": task_result.id,
                "status": "queued",
                "platforms": resolved_platforms,
            },
        }
