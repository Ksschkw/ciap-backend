"""
InfluenceScore entity model.

Stores the output of the ML scoring engine for each creator.
Separated into its own file because it is owned/written by the ML module
(Phase 2) but read by almost everything else.

Tables covered:
    InfluenceScore  - Versioned score record for a creator (append-only)
    ScoreBreakdown  - Sub-scores that compose the final influence score
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdown(BaseModel):
    """
    The weighted components that make up the final influence score.
    Stored alongside InfluenceScore so the frontend can explain the score
    to the creator ("Your audience loyalty is high but engagement quality is low").

    Not a standalone table — embedded as JSONB inside influence_scores.
    """
    audience_loyalty: float = Field(
        ..., ge=0.0, le=100.0,
        description="Repeat engagement rate from the same audience over time.",
    )
    engagement_quality: float = Field(
        ..., ge=0.0, le=100.0,
        description="Weighted engagement: comments > shares > likes > views.",
    )
    content_consistency: float = Field(
        ..., ge=0.0, le=100.0,
        description="Posting frequency and content schedule regularity.",
    )
    cross_platform_growth: float = Field(
        ..., ge=0.0, le=100.0,
        description="Follower growth rate across all connected platforms.",
    )
    conversion_probability: float = Field(
        ..., ge=0.0, le=100.0,
        description="Likelihood of driving real actions (clicks, purchases). Phase 2 feature.",
    )
    fraud_risk: float = Field(
        ..., ge=0.0, le=100.0,
        description="Estimated probability of inflated/purchased metrics (lower = better).",
    )


class InfluenceScore(BaseModel):
    """
    A versioned snapshot of a creator's influence score.
    The ML pipeline appends a new row weekly — old scores are never deleted,
    enabling trend tracking ("Your score grew 12% this month").

    Backend maps this to the `influence_scores` table.

    Indexes:
        - creator_id + scored_at DESC (primary access pattern)
        - scored_at DESC (for system-wide leaderboards)
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    creator_id: UUID = Field(..., description="FK → creator_profiles.id")

    # --- The single number creators see ---
    score: float = Field(
        ..., ge=0.0, le=100.0,
        description="Final composite influence score 0–100.",
    )

    # --- Explainability ---
    breakdown: ScoreBreakdown = Field(
        ...,
        description="JSONB. Sub-scores that explain the final score.",
    )

    # --- Model metadata (important for reproducibility) ---
    model_version: str = Field(
        ..., max_length=20,
        description="Version of the ML model that produced this score, e.g. 'v1.2.0'.",
    )
    data_window_days: int = Field(
        default=30, ge=1,
        description="How many days of historical data this score was computed over.",
    )
    platforms_included: list = Field(
        default_factory=list,
        description="Platforms whose data was used, e.g. ['YOUTUBE', 'INSTAGRAM']",
    )

    scored_at: datetime = Field(default_factory=datetime.utcnow)