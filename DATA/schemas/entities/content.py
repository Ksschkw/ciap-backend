"""
Content and metrics entity models.

Maps 1-to-1 with PostgreSQL tables defined in schema_erd.mmd.

Tables covered:
    ContentItem             - A single post/video/tweet fetched from a platform
    ContentMetricSnapshot   - Point-in-time metrics for a ContentItem (time-series)
    AudienceSnapshot        - Audience demographics snapshot per platform connection
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MediaType(str, enum.Enum):
    """Content format types that map across all platforms."""
    VIDEO = "VIDEO"         # YouTube video, TikTok, Instagram Reel
    IMAGE = "IMAGE"         # Instagram photo, Twitter image
    CAROUSEL = "CAROUSEL"   # Instagram carousel, LinkedIn carousel
    AUDIO = "AUDIO"         # Spotify track, Audiomack track, Twitter Spaces
    STORY = "STORY"         # Instagram / Snapchat story
    LIVE = "LIVE"           # Live stream (YouTube Live, Instagram Live)
    TEXT = "TEXT"           # Twitter/X text-only tweet, LinkedIn post
    SHORT = "SHORT"         # YouTube Shorts, TikTok (alias for SHORT-form video)


class ContentStatus(str, enum.Enum):
    """Tracks whether the content is still live or has been removed."""
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"       # Deleted by creator on original platform
    UNAVAILABLE = "UNAVAILABLE"  # Private, age-restricted, geo-blocked


# ---------------------------------------------------------------------------
# ContentItem (one row per post/video across all platforms)
# ---------------------------------------------------------------------------

class ContentItem(BaseModel):
    """
    A single piece of content published by a creator on any platform.
    Normalised from each platform's native API response format.

    Backend maps this to the `content_items` table.

    Indexes:
        - creator_id + platform (for per-platform listing)
        - external_id + platform (unique composite — deduplication key)
        - posted_at DESC (for chronological queries)
        - media_type
        - status
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    creator_id: UUID = Field(..., description="FK → creator_profiles.id")
    platform_connection_id: UUID = Field(
        ..., description="FK → platform_connections.id — which token fetched this."
    )

    # --- Platform identification ---
    platform: str = Field(..., description="Platform name (mirrors Platform enum).")
    external_id: str = Field(
        ..., description="Native post/video/track ID from the platform."
    )

    # --- Content metadata ---
    media_type: MediaType = Field(..., description="Normalised content format.")
    title: Optional[str] = Field(None, max_length=500, description="Video title, if applicable.")
    caption: Optional[str] = Field(None, description="Post caption / description.")
    hashtags: List[str] = Field(
        default_factory=list,
        description="Extracted hashtags from caption.",
    )
    permalink: Optional[str] = Field(None, description="Public URL to the original content.")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail/cover image URL.")

    # --- Duration (videos/audio only) ---
    duration_seconds: Optional[int] = Field(
        None, ge=0, description="Content duration. NULL for images/text."
    )

    # --- Timestamps ---
    posted_at: datetime = Field(..., description="When the creator originally published.")
    synced_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When CIAP last fetched this content.",
    )

    status: ContentStatus = Field(default=ContentStatus.ACTIVE)

    # --- Language detection (for sentiment analysis in Phase 2) ---
    detected_language: Optional[str] = Field(
        None, description="ISO 639-1 language code detected from caption/title."
    )


# ---------------------------------------------------------------------------
# ContentMetricSnapshot (time-series — one row per snapshot per content item)
# ---------------------------------------------------------------------------

class ContentMetricSnapshot(BaseModel):
    """
    Point-in-time metrics for a ContentItem.
    Each sync job appends a new row; we NEVER update old rows.
    This enables trend analysis and growth charts.

    Backend maps this to the `content_metric_snapshots` table.

    Indexes:
        - content_id + captured_at DESC (primary access pattern)
        - captured_at DESC (for system-wide queries)

    Partitioning (hint for Backend DBA):
        Partition by range on captured_at (monthly) for performance at scale.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    content_id: UUID = Field(..., description="FK → content_items.id")
    captured_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this metric snapshot was taken.",
    )

    # --- Core engagement metrics (all nullable — not every platform exposes all) ---
    views: Optional[int] = Field(None, ge=0)
    likes: Optional[int] = Field(None, ge=0)
    comments: Optional[int] = Field(None, ge=0)
    shares: Optional[int] = Field(None, ge=0)
    saves: Optional[int] = Field(None, ge=0, description="Bookmarks/saves (Instagram, TikTok).")
    reposts: Optional[int] = Field(None, ge=0, description="Retweets / reposts (Twitter/X).")

    # --- Video-specific metrics ---
    watch_time_seconds: Optional[int] = Field(
        None, ge=0, description="Total watch time in seconds (YouTube Analytics)."
    )
    average_view_duration_seconds: Optional[int] = Field(
        None, ge=0, description="Average viewer watch duration."
    )
    click_through_rate: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="CTR from impressions (YouTube)."
    )

    # --- Audio-specific metrics ---
    streams: Optional[int] = Field(None, ge=0, description="Stream count (Spotify/Audiomack).")
    playlist_adds: Optional[int] = Field(None, ge=0, description="Times added to playlists.")

    # --- Reach metrics ---
    impressions: Optional[int] = Field(None, ge=0, description="Total impressions/reach.")
    reach: Optional[int] = Field(None, ge=0, description="Unique accounts reached.")

    # --- Derived metric (calculated by normaliser, not pulled from API) ---
    engagement_rate: Optional[float] = Field(
        None,
        ge=0.0,
        description="(likes+comments+shares+saves) / reach * 100. Calculated on ingest.",
    )


# ---------------------------------------------------------------------------
# AudienceSnapshot (per platform, per creator — NOT per content item)
# ---------------------------------------------------------------------------

class AudienceSnapshot(BaseModel):
    """
    Demographic snapshot of a creator's audience on a specific platform.
    Fetched from platform analytics APIs (e.g., YouTube Analytics /reports).
    Stored as periodic snapshots (weekly) — no updates, only appends.

    Backend maps this to the `audience_snapshots` table.

    Indexes:
        - platform_connection_id + captured_at DESC
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    platform_connection_id: UUID = Field(..., description="FK → platform_connections.id")
    creator_id: UUID = Field(..., description="FK → creator_profiles.id")
    captured_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Follower / subscriber counts ---
    total_followers: Optional[int] = Field(None, ge=0)
    new_followers_this_period: Optional[int] = Field(None)

    # --- Demographics stored as JSON dicts (key=bucket, value=percentage 0–100) ---
    age_distribution: Optional[Dict[str, float]] = Field(
        None,
        description="e.g. {'13-17': 5.2, '18-24': 34.1, '25-34': 40.0, '35-44': 15.2, '45+': 5.5}",
    )
    gender_distribution: Optional[Dict[str, float]] = Field(
        None,
        description="e.g. {'male': 62.3, 'female': 36.1, 'other': 1.6}",
    )
    top_countries: Optional[Dict[str, float]] = Field(
        None,
        description="e.g. {'NG': 78.5, 'GH': 6.2, 'US': 4.1}",
    )
    top_cities: Optional[Dict[str, float]] = Field(
        None,
        description="e.g. {'Lagos': 45.2, 'Abuja': 18.3, 'Ibadan': 7.1}",
    )
    top_languages: Optional[Dict[str, float]] = Field(
        None,
        description="e.g. {'en': 82.0, 'yo': 9.0, 'ig': 5.0}",
    )