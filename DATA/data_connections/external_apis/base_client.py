"""
Abstract Base Client for all external social platform API integrations.

Every platform-specific client (YouTubeClient, InstagramClient, etc.)
MUST inherit from BaseAPIClient and implement all abstract methods.

This enforces:
    1. Consistent interface  — the ingestion service calls the same methods
       regardless of which platform it is fetching from.
    2. Normalised output     — every client's normalize_response() maps raw
       platform JSON to our unified ContentItem / ContentMetricSnapshot schemas.
    3. Testability           — the ingestion service can be unit-tested with
       a MockAPIClient that returns deterministic fixture data.

How to implement a new platform client (backend dev):
    1. Create a file: backend/data_connections/external_apis/youtube_client.py
    2. Define class YouTubeClient(BaseAPIClient)
    3. Set BASE_URL and PLATFORM_NAME class attributes
    4. Implement all 4 abstract methods: fetch_creator_data, normalize_response,
       fetch_audience_data, refresh_token, revoke_token
    5. Register it in the ingestion service factory map

See MockAPIClient at the bottom of this file as a working reference implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from DATA.schemas.entities.content import (
    AudienceSnapshot,
    ContentItem,
    ContentMetricSnapshot,
    ContentStatus,
    MediaType,
)
from DATA.schemas.entities.user import PlatformConnection


class BaseAPIClient(ABC):
    """
    Abstract base class for all social platform API clients.

    Attributes:
        BASE_URL      (str): The root API URL for this platform.
        PLATFORM_NAME (str): Must exactly match the Platform enum value
                             (e.g. "YOUTUBE", "INSTAGRAM").
        db_session         : Injected SQLAlchemy session for writing
                             audit logs mid-ingestion if needed.
    """

    BASE_URL: str = ""
    PLATFORM_NAME: str = ""

    def __init__(self, db_session: Any | None = None) -> None:
        self.db = db_session

    # ══════════════════════════════════════════════════════════════════════
    # CORE ABSTRACT METHODS — every platform client MUST implement these
    # ══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def fetch_creator_data(
        self,
        connection: PlatformConnection,
        since: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch a creator's content and metrics from the platform API.

        Args:
            connection: The PlatformConnection row. access_token has already
                        been decrypted by the ingestion service before this call.
            since:      If given, only fetch content posted AFTER this datetime
                        (incremental sync). If None, fetch everything (initial sync).

        Returns:
            Tuple:
                [0] raw_content_list  — list of raw API dict per post/video/track
                [1] raw_metrics_list  — list of raw API dict per metric payload
                    (may be the same dicts if the platform bundles them together,
                    or separate calls if the platform separates content and analytics)

        Implementation notes:
            - Handle pagination internally (loop until no next_page_token / cursor).
            - Catch HTTP 429 / quota errors and raise RateLimitError.
            - Log the start/end of each sync run to AuditLog via audit_repo.
            - Never log access_token values.

        YouTube example:
            GET https://www.googleapis.com/youtube/v3/search
                ?part=snippet&forMine=true&type=video&maxResults=50
                &publishedAfter={since.isoformat()}Z
        """
        ...

    @abstractmethod
    def normalize_response(
        self,
        raw_content: Dict[str, Any],
        raw_metrics: Dict[str, Any],
        connection: PlatformConnection,
    ) -> Tuple[ContentItem, Optional[ContentMetricSnapshot]]:
        """
        Map a single raw platform API response to our unified schema.

        Args:
            raw_content:  One item from raw_content_list (one post/video/track).
            raw_metrics:  The corresponding metrics dict (may be the same object
                          if the platform bundles them; may be empty dict if metrics
                          are fetched separately and not yet available).
            connection:   Used to set creator_id, platform, platform_connection_id.

        Returns:
            Tuple:
                [0] ContentItem                 — ready to upsert via IContentRepository
                [1] ContentMetricSnapshot|None  — ready to insert via IContentMetricRepository
                    None when metrics are absent in this payload.

        Platform field mappings (expand as you add platforms):

            YouTube Data API v3 → ContentItem:
                snippet.resourceId.videoId      → external_id
                snippet.title                   → title
                snippet.description             → caption
                snippet.tags                    → hashtags
                snippet.publishedAt             → posted_at
                snippet.thumbnails.default.url  → thumbnail_url
                contentDetails.duration         → duration_seconds (parse ISO 8601)

            YouTube Analytics API → ContentMetricSnapshot:
                statistics.viewCount            → views
                statistics.likeCount            → likes
                statistics.commentCount         → comments
                statistics.favoriteCount        → saves

            Instagram Graph API → ContentItem:
                id                              → external_id
                caption                         → caption (parse hashtags from here)
                media_type                      → media_type
                timestamp                       → posted_at
                permalink                       → permalink
                thumbnail_url                   → thumbnail_url

            Instagram Insights → ContentMetricSnapshot:
                impressions                     → impressions
                reach                           → reach
                likes                           → likes
                comments                        → comments
                saved                           → saves
                shares                          → shares

            TikTok Research API → ContentItem:
                video_id                        → external_id
                title                           → title
                video_description               → caption
                create_time                     → posted_at
                cover_image_url                 → thumbnail_url
                duration                        → duration_seconds

            Spotify Web API → ContentItem:
                id                              → external_id
                name                            → title
                (no caption — leave None)
                release_date                    → posted_at
                duration_ms / 1000              → duration_seconds (convert)
                album.images[0].url             → thumbnail_url

            Spotify Track → ContentMetricSnapshot:
                popularity (0-100 index)        → store in a custom_data JSONB field
                (Spotify does not expose stream counts via public API — use mock)
        """
        ...

    @abstractmethod
    async def fetch_audience_data(
        self,
        connection: PlatformConnection,
    ) -> Optional[AudienceSnapshot]:
        """
        Fetch audience demographic data for this creator from the platform.
        This is typically a SEPARATE API call from content data.

        Returns:
            AudienceSnapshot ready for insert_snapshot(), or None if the
            platform does not expose audience data (e.g. Audiomack free tier,
            Twitter Basic tier).

        Platform endpoints:
            YouTube Analytics API:
                GET /reports?dimensions=ageGroup,gender&metrics=viewerPercentage
                GET /reports?dimensions=country&metrics=views
            Instagram Graph API:
                GET /{ig-user-id}/insights
                    ?metric=follower_demographics
                    &period=lifetime
                    &breakdown=age,gender,country,city
            TikTok Research API:
                POST /research/user/info/
        """
        ...

    @abstractmethod
    async def refresh_token(
        self,
        connection: PlatformConnection,
    ) -> Tuple[str, Optional[str], Optional[datetime]]:
        """
        Exchange the refresh_token for a new access_token.

        Returns:
            Tuple of (new_access_token, new_refresh_token_or_none, new_expiry_or_none).
            new_refresh_token is None when the platform does NOT rotate refresh tokens.
            new_expiry is None for non-expiring tokens.

        Implementation notes:
            - ENCRYPT the new tokens BEFORE calling
              IPlatformConnectionRepository.update_tokens().
            - If the refresh call returns HTTP 401/400 (token permanently revoked),
              call IPlatformConnectionRepository.mark_inactive() then raise
              TokenRevokedError so the ingestion scheduler stops retrying.
        """
        ...

    @abstractmethod
    async def revoke_token(
        self,
        connection: PlatformConnection,
    ) -> bool:
        """
        Call the platform's token revocation endpoint.
        Called when a user disconnects a platform from their settings.

        Returns True on success, False if the platform call failed.
        The caller (service layer) will call mark_inactive() regardless of
        the return value, so the local connection is deactivated either way.
        """
        ...

    # ══════════════════════════════════════════════════════════════════════
    # SHARED HELPERS — concrete, available to all subclasses
    # ══════════════════════════════════════════════════════════════════════

    def get_headers(self, access_token: str) -> Dict[str, str]:
        """
        Build standard Bearer token Authorization header.
        Override in subclasses if the platform uses a different auth scheme.
        (e.g. Spotify uses Authorization: Bearer but also needs Content-Type)
        """
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def calculate_engagement_rate(
        self,
        likes: Optional[int],
        comments: Optional[int],
        shares: Optional[int],
        saves: Optional[int],
        reach: Optional[int],
    ) -> Optional[float]:
        """
        Normalised engagement rate formula used across ALL platforms:
            (likes + comments + shares + saves) / reach * 100

        Returns None if reach is 0 or unavailable (avoids division by zero).
        The result is stored in ContentMetricSnapshot.engagement_rate.
        """
        if not reach or reach == 0:
            return None
        interactions = sum(x for x in [likes, comments, shares, saves] if x is not None)
        return round((interactions / reach) * 100, 4)

    def safe_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        """
        Safely convert a raw API value to int.
        Platforms often return counts as strings ("1234") or null.
        """
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def safe_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert a raw API value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default


# ══════════════════════════════════════════════════════════════════════════════
# MockAPIClient — used for all platforms EXCEPT YouTube during Week 2
# ══════════════════════════════════════════════════════════════════════════════

class MockAPIClient(BaseAPIClient):
    """
    Returns deterministic fixture data instead of calling a real API.

    Use this for:
        - Instagram (week 2 mock)
        - TikTok    (week 2 mock)
        - Twitter   (week 2 mock)
        - Spotify   (week 2 mock)
        - Audiomack (week 2 mock)
        - Snapchat  (week 2 mock)

    The backend dev registers each platform mock in the ingestion service factory:
        PLATFORM_CLIENTS = {
            "YOUTUBE":   YouTubeClient,
            "INSTAGRAM": MockAPIClient,   # swap for InstagramClient in week 4
            "TIKTOK":    MockAPIClient,
            ...
        }
    """

    BASE_URL = "https://mock.ciap.internal"
    PLATFORM_NAME = "MOCK"

    async def fetch_creator_data(
        self,
        connection: PlatformConnection,
        since: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Returns two fixture content items with embedded metrics."""
        raw_content = [
            {
                "id": "mock_video_001",
                "title": "Mock Video 1",
                "description": "This is a mock video #test #mock",
                "published_at": "2026-04-01T10:00:00Z",
                "thumbnail": "https://via.placeholder.com/320x180",
                "duration_seconds": 360,
                "views": 10000,
                "likes": 800,
                "comments": 120,
                "shares": 55,
                "saves": 30,
                "reach": 15000,
                "impressions": 22000,
            },
            {
                "id": "mock_video_002",
                "title": "Mock Video 2",
                "description": "Second mock piece of content #ciap",
                "published_at": "2026-04-05T14:30:00Z",
                "thumbnail": "https://via.placeholder.com/320x180",
                "duration_seconds": 185,
                "views": 5500,
                "likes": 430,
                "comments": 67,
                "shares": 22,
                "saves": 15,
                "reach": 8000,
                "impressions": 11000,
            },
        ]
        return raw_content, raw_content  # metrics bundled in same dict for mock

    def normalize_response(
        self,
        raw_content: Dict[str, Any],
        raw_metrics: Dict[str, Any],
        connection: PlatformConnection,
    ) -> Tuple[ContentItem, Optional[ContentMetricSnapshot]]:
        """Maps mock fixture fields to unified ContentItem + ContentMetricSnapshot."""
        from datetime import timezone

        now = datetime.now(timezone.utc)

        content = ContentItem(
            creator_id=connection.user_id,
            platform_connection_id=connection.id,
            platform=connection.platform_name,
            external_id=raw_content["id"],
            media_type=MediaType.VIDEO,
            title=raw_content.get("title"),
            caption=raw_content.get("description"),
            hashtags=[
                tag.strip("#")
                for word in (raw_content.get("description") or "").split()
                if word.startswith("#")
                for tag in [word]
            ],
            permalink=None,
            thumbnail_url=raw_content.get("thumbnail"),
            duration_seconds=raw_content.get("duration_seconds"),
            posted_at=datetime.fromisoformat(
                raw_content["published_at"].replace("Z", "+00:00")
            ),
            synced_at=now,
            status=ContentStatus.ACTIVE,
            detected_language=None,
        )

        reach = self.safe_int(raw_metrics.get("reach"))
        likes = self.safe_int(raw_metrics.get("likes"))
        comments = self.safe_int(raw_metrics.get("comments"))
        shares = self.safe_int(raw_metrics.get("shares"))
        saves = self.safe_int(raw_metrics.get("saves"))

        snapshot = ContentMetricSnapshot(
            content_id=content.id,
            captured_at=now,
            views=self.safe_int(raw_metrics.get("views")),
            likes=likes,
            comments=comments,
            shares=shares,
            saves=saves,
            reposts=None,
            watch_time_seconds=None,
            average_view_duration_seconds=None,
            click_through_rate=None,
            streams=None,
            playlist_adds=None,
            impressions=self.safe_int(raw_metrics.get("impressions")),
            reach=reach,
            engagement_rate=self.calculate_engagement_rate(
                likes, comments, shares, saves, reach
            ),
        )
        return content, snapshot

    async def fetch_audience_data(
        self,
        connection: PlatformConnection,
    ) -> Optional[AudienceSnapshot]:
        """Returns a fixture audience snapshot with Nigerian demographic distribution."""
        return AudienceSnapshot(
            platform_connection_id=connection.id,
            creator_id=connection.user_id,
            total_followers=50000,
            new_followers_this_period=1200,
            age_distribution={"13-17": 5.0, "18-24": 38.0, "25-34": 35.0, "35-44": 14.0, "45+": 8.0},
            gender_distribution={"male": 58.0, "female": 40.0, "other": 2.0},
            top_countries={"NG": 72.0, "GH": 8.0, "US": 6.0, "GB": 4.0, "ZA": 3.0},
            top_cities={"Lagos": 40.0, "Abuja": 15.0, "Port Harcourt": 8.0, "Ibadan": 6.0},
            top_languages={"en": 78.0, "yo": 10.0, "ig": 7.0, "ha": 5.0},
        )

    async def refresh_token(
        self,
        connection: PlatformConnection,
    ) -> Tuple[str, Optional[str], Optional[datetime]]:
        """Mock returns the same token — no real refresh needed."""
        return connection.access_token, connection.refresh_token, connection.token_expires_at

    async def revoke_token(self, connection: PlatformConnection) -> bool:
        """Mock always succeeds."""
        return True