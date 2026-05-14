from __future__ import annotations

from typing import Any

from app.tasks.celery_app import celery_app


@celery_app.task(name="sync.platform_data", bind=True)
def sync_platform_data(
    self: Any,
    user_id: str | None = None,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "message": "Platform sync queued",
        "data": {
            "task_id": self.request.id,
            "status": "queued",
            "user_id": user_id,
            "platforms": platforms or [],
        },
    }
