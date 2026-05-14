from __future__ import annotations

from typing import Any

from app.tasks.celery_app import celery_app


@celery_app.task(name="reports.generate_campaign", bind=True)
def generate_campaign_report(
    self: Any,
    campaign_id: str,
    export_format: str = "pdf",
) -> dict[str, Any]:
    return {
        "success": True,
        "message": "Report generation queued",
        "data": {
            "task_id": self.request.id,
            "campaign_id": campaign_id,
            "format": export_format,
            "status": "queued",
        },
    }
