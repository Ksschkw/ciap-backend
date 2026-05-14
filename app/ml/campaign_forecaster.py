from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.ml.feature_engineering import extract_numeric_features


@dataclass(slots=True)
class CampaignForecastResult:
    predicted_reach: int
    predicted_engagement: int
    predicted_conversions: int
    predicted_roi: float
    confidence_score: float
    details: dict[str, Any]


@dataclass(slots=True)
class CampaignForecaster:
    def forecast(
        self,
        creator_metrics: Mapping[str, Any],
        budget: float,
        duration_days: int,
        goal: str,
    ) -> CampaignForecastResult:
        features = extract_numeric_features(creator_metrics)
        influence_score = features.get("influence_score", features.get("score", 50.0))
        reach_base = max(features.get("views", 0.0), features.get("followers", 0.0) * 1.5)
        budget_factor = max(budget / 100000.0, 1.0)
        duration_factor = max(duration_days / 7.0, 1.0)

        predicted_reach = int(reach_base * (1.0 + influence_score / 200.0) * budget_factor ** 0.25)
        predicted_engagement = int(predicted_reach * max(features.get("engagement_rate", 0.05), 0.03))
        goal_multiplier = 1.2 if goal.lower() in {"conversion", "roi"} else 1.0
        predicted_conversions = max(1, int(predicted_engagement * 0.02 * goal_multiplier))
        predicted_roi = round((predicted_conversions * 1000.0) / max(budget, 1.0), 2)
        confidence_score = round(min(0.95, 0.45 + (influence_score / 200.0) + min(duration_factor, 3.0) * 0.05), 2)

        return CampaignForecastResult(
            predicted_reach=predicted_reach,
            predicted_engagement=predicted_engagement,
            predicted_conversions=predicted_conversions,
            predicted_roi=predicted_roi,
            confidence_score=confidence_score,
            details={"goal": goal, "budget": budget, "duration_days": duration_days},
        )
