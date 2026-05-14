from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.schemas import ForecastRequest
from DATA.data_connections.repositories import (
    SQLCreatorProfileRepository,
    SQLInfluenceScoreRepository,
    SQLContentMetricRepository,
)
from app.ml.campaign_forecaster import CampaignForecaster
from app.utils.serialization import model_to_dict


@dataclass(slots=True)
class ForecastService:
    session: Session

    def forecast_campaign(self, payload: ForecastRequest) -> dict[str, Any]:
        metric_repo = SQLContentMetricRepository(self.session)
        score_repo = SQLInfluenceScoreRepository(self.session)
        profile_repo = SQLCreatorProfileRepository(self.session)

        latest_metric = metric_repo.latest_for_user(payload.creator_id)
        latest_score = score_repo.latest_for_creator(payload.creator_id)
        profile = profile_repo.get_by_user_id(payload.creator_id)

        metrics = model_to_dict(latest_metric).get("metrics", {}) if latest_metric is not None else {}
        metrics["followers"] = profile.followers if profile is not None and profile.followers is not None else metrics.get("followers", 0)
        metrics["influence_score"] = latest_score.score if latest_score is not None else (profile.influence_score if profile is not None and profile.influence_score is not None else 0.0)

        result = CampaignForecaster().forecast(metrics, budget=payload.budget, duration_days=payload.duration_days, goal=payload.goal)
        return {"success": True, "message": "Forecast generated successfully", "data": {"creator_id": str(payload.creator_id), **asdict(result)}}
