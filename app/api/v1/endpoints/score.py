from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_score_service
from app.dependencies import get_current_user
from app.services.score_service import ScoreService

router = APIRouter(prefix="/score", tags=["score"])


@router.get("/{creator_id}", summary="Get Creator Score", response_description="Current influence score details")
def current_score(
    creator_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    score_service: ScoreService = Depends(get_score_service),
) -> dict[str, object]:
    """
    Retrieve the current computed influence score for a specific creator.
    
    This includes the overall score value (0-100) and the specific tier (e.g., Micro, Macro).
    """
    return score_service.get_current_score(creator_id)


@router.get("/{creator_id}/history", summary="Get Score History", response_description="Time-series data of score changes")
def score_history(
    creator_id: UUID,
    current_user: dict[str, str] = Depends(get_current_user),
    score_service: ScoreService = Depends(get_score_service),
) -> dict[str, object]:
    """
    Retrieve the historical tracking of a creator's influence score over time.
    
    Returns an array of data points suitable for rendering a trend chart on the frontend.
    """
    return score_service.get_score_history(creator_id)


@router.post("/compute", summary="Compute/Update Score", response_description="The newly computed score")
def compute_score(
    creator_id: UUID = Query(..., description="UUID of the creator to score"),
    force: bool = Query(default=False, description="Force recomputation even if recently computed"),
    current_user: dict[str, str] = Depends(get_current_user),
    score_service: ScoreService = Depends(get_score_service),
) -> dict[str, object]:
    """
    Trigger a manual recalculation of a creator's influence score.
    
    This processes their latest connected platform analytics (followers, engagement rate, etc.)
    through our proprietary algorithm to generate an updated score.
    """
    return score_service.compute_score(creator_id, force=force)
