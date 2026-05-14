from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from DATA.models.scoring import InfluenceScore
from DATA.data_connections.repositories import (
    SQLAudienceSnapshotRepository,
    SQLInfluenceScoreRepository,
    SQLContentMetricRepository,
)
from app.ml.influence_scorer import InfluenceScorer
from app.utils.date_utils import utcnow
from app.utils.serialization import model_to_dict, models_to_dicts


@dataclass(slots=True)
class ScoreService:
    session: Session

    def _build_score_snapshot(self, creator_id: UUID) -> dict[str, Any]:
        metric_repo   = SQLContentMetricRepository(self.session)
        audience_repo = SQLAudienceSnapshotRepository(self.session)
        score_repo    = SQLInfluenceScoreRepository(self.session)

        # Resolve profile_id — creator_id could be either user.id or creator_profile.id
        from DATA.data_connections.repositories import SQLCreatorProfileRepository
        from app.core.exceptions import NotFoundError
        profile_repo = SQLCreatorProfileRepository(self.session)
        
        profile = profile_repo.get_by_user_id(creator_id)
        if not profile:
            profile = profile_repo.get_by_id(creator_id)
            
        if not profile:
            raise NotFoundError("Creator profile not found. Please connect a platform and sync data first.")
            
        profile_id = profile.id

        latest_metrics  = metric_repo.get_aggregated_for_creator(profile_id)
        latest_audience = audience_repo.latest_for_creator(profile_id)
        audience_values = model_to_dict(latest_audience) if latest_audience is not None else {}

        latest_score = score_repo.latest_for_creator(profile_id)
        if latest_score is not None:
            return model_to_dict(latest_score)

        result = InfluenceScorer().score(latest_metrics, audience_values)
        score = InfluenceScore(
            creator_id=profile_id,          # FK to creator_profiles.id
            score=result.score,
            breakdown=result.components,    # correct column: breakdown
            model_version=result.model_version,
            scored_at=utcnow(),             # correct column: scored_at
        )
        score_repo.insert_score(score)
        self.session.commit()
        self.session.refresh(score)
        return model_to_dict(score)

    def get_current_score(self, creator_id: UUID) -> dict[str, Any]:
        score_snapshot = self._build_score_snapshot(creator_id)
        return {
            "success": True,
            "message": "Influence score retrieved",
            "data": {
                "creator_id": str(creator_id),
                **score_snapshot,
            },
        }

    def get_score_history(self, creator_id: UUID) -> dict[str, Any]:
        from DATA.data_connections.repositories import SQLCreatorProfileRepository
        from app.core.exceptions import NotFoundError
        profile_repo = SQLCreatorProfileRepository(self.session)
        
        profile = profile_repo.get_by_user_id(creator_id)
        if not profile:
            profile = profile_repo.get_by_id(creator_id)
            
        if not profile:
            raise NotFoundError("Creator profile not found. Please connect a platform and sync data first.")
        
        history = SQLInfluenceScoreRepository(self.session).get_history_for_creator(profile.id, limit=20)
        return {
            "success": True,
            "message": "Score history retrieved",
            "data": {
                "creator_id": str(creator_id),
                "series": [
                    {"scored_at": s.scored_at.isoformat() if s.scored_at else None, "score": s.score}
                    for s in reversed(history)
                ],
            },
        }

    def compute_score(self, creator_id: UUID, force: bool = False) -> dict[str, Any]:
        from DATA.data_connections.repositories import SQLCreatorProfileRepository
        from app.core.exceptions import NotFoundError
        profile_repo = SQLCreatorProfileRepository(self.session)
        
        profile = profile_repo.get_by_user_id(creator_id)
        if not profile:
            profile = profile_repo.get_by_id(creator_id)
            
        if not profile:
            raise NotFoundError("Creator profile not found. Please connect a platform and sync data first.")

        score_repo = SQLInfluenceScoreRepository(self.session)
        latest_score = score_repo.latest_for_creator(profile.id)
        if latest_score is not None and not force:
            score_snapshot = model_to_dict(latest_score)
        else:
            score_snapshot = self._build_score_snapshot(creator_id)
            
        return {
            "success": True,
            "message": "Score recomputed successfully",
            "data": {
                "creator_id": str(creator_id),
                "force": force,
                "score": score_snapshot,
            },
        }
