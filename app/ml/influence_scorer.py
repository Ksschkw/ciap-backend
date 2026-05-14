from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.ml.feature_engineering import extract_numeric_features
from app.utils.date_utils import isoformat, utcnow


@dataclass(slots=True)
class InfluenceScoreResult:
    score: float
    model_version: str
    computed_at: str
    components: dict[str, float]


@dataclass(slots=True)
class InfluenceScorer:
    model_version: str = "conversion_weighted_v2"
    base_weights: dict[str, float] = field(
        default_factory=lambda: {
            "engagement": 0.45,
            "growth": 0.35,
            "consistency": 0.0,
            "audience_quality": 0.20,
        }
    )
    conversion_weights: dict[str, float] = field(
        default_factory=lambda: {
            "conversion": 0.45,
            "engagement": 0.25,
            "growth": 0.15,
            "audience_quality": 0.15,
        }
    )

    def score(self, metrics: Mapping[str, Any], audience: Mapping[str, Any] | None = None, past_performance: Mapping[str, Any] | None = None) -> InfluenceScoreResult:
        feature_map = extract_numeric_features(metrics)
        audience_map = extract_numeric_features(audience or {})
        perf_map = extract_numeric_features(past_performance or {})

        total_conversions = perf_map.get("total_conversions", 0.0)
        
        engagement_component = min(
            (feature_map.get("engagement_rate", 0.0) * 50.0)
            + (feature_map.get("likes", 0.0) / 1000.0)
            + (feature_map.get("comments", 0.0) / 2000.0),
            100.0,
        )
        growth_component = min(
            (feature_map.get("growth_rate", 0.0) * 60.0)
            + (feature_map.get("follower_growth", 0.0) * 60.0),
            100.0,
        )
        audience_quality_component = min(
            (audience_map.get("quality", 0.0) * 20.0)
            + (audience_map.get("interest_tags.count", 0.0) * 1.5),
            100.0,
        )
        
        conversion_component = min(total_conversions * 5.0, 100.0) # Assume 20+ conversions = max score

        if total_conversions > 0:
            weights = self.conversion_weights
            score = (
                (conversion_component * weights["conversion"])
                + (engagement_component * weights["engagement"])
                + (growth_component * weights["growth"])
                + (audience_quality_component * weights["audience_quality"])
            )
        else:
            weights = self.base_weights
            score = (
                (engagement_component * weights["engagement"])
                + (growth_component * weights["growth"])
                + (audience_quality_component * weights["audience_quality"])
            )

        score = round(score, 2)
        
        return InfluenceScoreResult(
            score=min(score, 100.0),
            model_version=self.model_version,
            computed_at=isoformat(utcnow()),
            components={
                "conversion_component": round(conversion_component, 2),
                "engagement_component": round(engagement_component, 2),
                "growth_component": round(growth_component, 2),
                "audience_quality_component": round(audience_quality_component, 2),
            },
        )
