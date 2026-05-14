from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_score_service
from app.dependencies import get_current_user
from app.services.score_service import ScoreService

router = APIRouter(prefix="/score", tags=["score"])


@router.get("/{creator_id}")
def current_score(
    creator_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    score_service: ScoreService = Depends(get_score_service),
) -> dict[str, object]:
    return score_service.get_current_score(creator_id)


@router.get("/{creator_id}/history")
def score_history(
    creator_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    score_service: ScoreService = Depends(get_score_service),
) -> dict[str, object]:
    return score_service.get_score_history(creator_id)


@router.post("/compute")
def compute_score(
    creator_id: UUID = Query(...),
    force: bool = Query(default=False),
    current_user: dict[str, str] = Depends(get_current_user),
    score_service: ScoreService = Depends(get_score_service),
) -> dict[str, object]:
    return score_service.compute_score(creator_id, force=force)
