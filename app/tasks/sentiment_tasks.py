from __future__ import annotations

from typing import Any

from app.tasks.celery_app import celery_app


@celery_app.task(name="sentiment.process_content", bind=True)
def process_content_sentiment(
    self: Any,
    content_id: str,
    comments: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "message": "Sentiment processing queued",
        "data": {"task_id": self.request.id, "content_id": content_id, "comments": comments or []},
    }
