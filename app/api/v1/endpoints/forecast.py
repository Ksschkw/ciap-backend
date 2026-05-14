from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas import ForecastRequest
from app.dependencies import get_current_user, get_forecast_service
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post(
    "/campaign",
    summary="Campaign Performance Forecast",
    response_description="Predicted reach, engagement, conversions, and ROI for a creator/campaign combo",
)
def forecast_campaign(
    payload: ForecastRequest,
    current_user: dict[str, str] = Depends(get_current_user),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> dict[str, object]:
    """
    **SME endpoint.** Predict campaign performance before booking.

    Provide a `creator_id`, your intended `budget` (NGN), `duration_days`,
    and `goal` (e.g. `awareness`, `conversion`, `roi`).

    Returns:
    - `predicted_reach` — estimated total impressions
    - `predicted_engagement` — estimated likes/comments/shares
    - `predicted_conversions` — estimated goal completions
    - `predicted_roi` — return on investment multiplier
    - `confidence_score` — model confidence (0–1)
    """
    return forecast_service.forecast_campaign(payload)


@router.get(
    "/creator/{creator_id}/smart-insights",
    summary="Creator Smart Insights (Expected Reach)",
    response_description="Quick projected metrics for a creator — no form required",
)
def creator_smart_insights(
    creator_id: UUID,
    budget: float = Query(default=500_000.0, gt=0, description="Hypothetical campaign budget in NGN (default: ₦500,000)"),
    duration_days: int = Query(default=30, gt=0, description="Hypothetical campaign duration in days (default: 30)"),
    goal: str = Query(default="awareness", description="Campaign goal: awareness | conversion | roi"),
    current_user: dict[str, str] = Depends(get_current_user),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> dict[str, object]:
    """
    **SME endpoint.** Zero-friction "Smart Insights" for a creator profile page.

    The frontend can call this with **no user input** (all params have sensible
    defaults) to display projected performance metrics — Expected Reach,
    Expected Engagement, Confidence Score — directly on the creator's card or
    detail page.

    The SME can also tweak the `budget` / `duration_days` / `goal` query params
    to run custom "what-if" scenarios without leaving the profile view.

    Uses the creator's real historical metrics and influence score from the DB.
    """
    payload = ForecastRequest(
        creator_id=creator_id,
        budget=budget,
        duration_days=duration_days,
        goal=goal,
    )
    result = forecast_service.forecast_campaign(payload)
    # Rename data key so the frontend knows this is a lightweight "smart insight"
    # rather than a full campaign forecast
    if isinstance(result.get("data"), dict):
        result["data"]["insight_type"] = "smart_insights"
        result["data"]["defaults_used"] = {
            "budget": budget,
            "duration_days": duration_days,
            "goal": goal,
        }
    return result
