from __future__ import annotations

from typing import Any

from app.tasks.celery_app import celery_app


@celery_app.task(name="score.recompute_creator", bind=True)
def recompute_creator_score(
    self: Any,
    creator_id: str,
    force: bool = False,
) -> dict[str, Any]:
    return {
        "success": True,
        "message": "Score recomputation queued",
        "data": {"task_id": self.request.id, "creator_id": creator_id, "force": force},
    }
