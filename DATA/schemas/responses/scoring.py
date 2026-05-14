"""
Response models for the ML Influence Scoring endpoints.

Returned by GET /creator/score and GET /creator/score/history.

Classes:
    ScoreBreakdownResponse  - Explained sub-scores with labels and tips
    InfluenceScoreResponse  - Full current score detail for a creator
    ScoreHistoryPoint       - One point on the score trend chart
    ScoreHistoryResponse    - Time-series score history for the growth chart
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Score breakdown with frontend-friendly labels and tips
# ---------------------------------------------------------------------------

class ScoreDimensionDetail(BaseModel):
    """
    One dimension of the influence score with a human-readable label,
    value, and an actionable tip — so the creator knows what to improve.
    """
    key: str = Field(..., description="Machine key, e.g. 'audience_loyalty'.")
    label: str = Field(..., description="Human label, e.g. 'Audience Loyalty'.")
    value: float = Field(..., ge=0.0, le=100.0)
    weight_pct: float = Field(
        ..., ge=0.0, le=100.0,
        description="How much this dimension contributes to the final score.",
    )
    tip: Optional[str] = Field(
        None,
        description="Actionable improvement tip shown when value < 60.",
    )


class ScoreBreakdownResponse(BaseModel):
    """
    Detailed breakdown of the influence score with labels and tips.
    Used in the score detail panel on the Creator Dashboard.
    """
    dimensions: List[ScoreDimensionDetail]
    fraud_risk_level: str = Field(
        ..., description="'LOW' | 'MEDIUM' | 'HIGH' — derived from fraud_risk sub-score."
    )


# ---------------------------------------------------------------------------
# Current score
# ---------------------------------------------------------------------------

class InfluenceScoreResponse(BaseModel):
    """
    Returned by GET /creator/score.
    The creator's most recent influence score with full breakdown.
    """
    creator_profile_id: UUID
    score: float = Field(..., ge=0.0, le=100.0)
    score_label: str = Field(
        ...,
        description="Tier label: 'Rising' (0–39) | 'Established' (40–64) | "
                    "'Influential' (65–84) | 'Elite' (85–100).",
    )
    breakdown: ScoreBreakdownResponse
    model_version: str
    platforms_included: List[str]
    data_window_days: int
    scored_at: datetime

    # Change vs previous score
    previous_score: Optional[float] = None
    score_change: Optional[float] = Field(
        None, description="Positive = improved, Negative = declined."
    )
    score_change_pct: Optional[float] = None


# ---------------------------------------------------------------------------
# Score history (trend chart)
# ---------------------------------------------------------------------------

class ScoreHistoryPoint(BaseModel):
    """One data point on the score trend chart."""
    scored_at: datetime
    score: float
    model_version: str


class ScoreHistoryResponse(BaseModel):
    """
    Returned by GET /creator/score/history.
    Historical score trend for the Creator Dashboard growth chart.
    """
    creator_profile_id: UUID
    history: List[ScoreHistoryPoint]
    current_score: Optional[float]