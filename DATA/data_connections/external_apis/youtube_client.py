from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient import *
import os

from DATA.data_connections.external_apis.base_client import BaseAPIClient
from DATA.models.users import PlatformConnection
from DATA.schemas.entities.content import ContentItem, ContentMetricSnapshot, MediaType, ContentStatus, AudienceSnapshot

class YouTubeClient(BaseAPIClient):
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    PLATFORM_NAME = "YOUTUBE"

    def __init__(self, db_session=None):
        super().__init__(db_session)
        # Using API key for public data, but if OAuth is needed it can be passed via connection
        self.api_key = os.environ.get("YOUTUBE_API_KEY", "")

    async def fetch_creator_data(
        self,
        connection: PlatformConnection,
        since: Optional[datetime] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        # Fallback to API Key if access_token is empty or not provided
        youtube = build("youtube", "v3", developerKey=self.api_key)

        # 1. Fetch Channel Statistics (which includes total views and subscribers)
        # Assuming connection.platform_user_id is the YouTube Channel ID
        channel_response = youtube.channels().list(
            part="statistics",
            id=connection.platform_user_id
        ).execute()

        channel_stats = {}
        if channel_response.get("items"):
            channel_stats = channel_response["items"][0].get("statistics", {})

        # 2. Fetch Latest Videos (mocking simple search query for the channel)
        search_request = youtube.search().list(
            part="snippet",
            channelId=connection.platform_user_id,
            maxResults=5,
            order="date",
            type="video"
        )
        if since:
            search_request = youtube.search().list(
                part="snippet",
                channelId=connection.platform_user_id,
                maxResults=5,
                order="date",
                type="video",
                publishedAfter=since.isoformat() + "Z" if not since.tzinfo else since.isoformat()
            )

        search_response = search_request.execute()
        
        video_ids = [item["id"]["videoId"] for item in search_response.get("items", []) if item["id"].get("videoId")]

        raw_content_list = []
        raw_metrics_list = []

        if video_ids:
            # 3. Fetch detailed video stats
            videos_response = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(video_ids)
            ).execute()

            for video in videos_response.get("items", []):
                raw_content_list.append(video)
                raw_metrics_list.append(video)

        # Append channel stats so we can update total_followers and total_views if needed
        # We handle this in the service layer, but we just return content and metrics here
        return raw_content_list, raw_metrics_list

    def normalize_response(
        self,
        raw_content: Dict[str, Any],
        raw_metrics: Dict[str, Any],
        connection: PlatformConnection,
    ) -> Tuple[ContentItem, Optional[ContentMetricSnapshot]]:
        
        snippet = raw_content.get("snippet", {})
        statistics = raw_metrics.get("statistics", {})
        
        posted_at_str = snippet.get("publishedAt")
        if posted_at_str:
            posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
        else:
            posted_at = datetime.now(timezone.utc)

        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = None
        if "high" in thumbnails:
            thumbnail_url = thumbnails["high"].get("url")
        elif "default" in thumbnails:
            thumbnail_url = thumbnails["default"].get("url")

        content = ContentItem(
            id=None,  # Handled by DB
            creator_id=connection.user_id,
            platform_connection_id=connection.id,
            platform=self.PLATFORM_NAME,
            external_id=raw_content.get("id"),
            media_type=MediaType.VIDEO,
            title=snippet.get("title"),
            caption=snippet.get("description"),
            hashtags=snippet.get("tags", []),
            permalink=f"https://www.youtube.com/watch?v={raw_content.get('id')}",
            thumbnail_url=thumbnail_url,
            duration_seconds=0, # Parse ISO 8601 duration from contentDetails if needed
            posted_at=posted_at,
            synced_at=datetime.now(timezone.utc),
            status=ContentStatus.ACTIVE,
            detected_language=snippet.get("defaultLanguage"),
        )

        likes = self.safe_int(statistics.get("likeCount", 0))
        comments = self.safe_int(statistics.get("commentCount", 0))
        views = self.safe_int(statistics.get("viewCount", 0))

        snapshot = ContentMetricSnapshot(
            id=None,
            content_id=None, # Will be set by DB
            captured_at=datetime.now(timezone.utc),
            views=views,
            likes=likes,
            comments=comments,
            shares=0,
            saves=0,
            reposts=0,
            watch_time_seconds=0,
            average_view_duration_seconds=0,
            click_through_rate=0.0,
            streams=0,
            playlist_adds=0,
            impressions=0,
            reach=views, # Approximate reach as views
            engagement_rate=self.calculate_engagement_rate(likes, comments, 0, 0, views)
        )
        return content, snapshot

    async def fetch_audience_data(
        self,
        connection: PlatformConnection,
    ) -> Optional[AudienceSnapshot]:
        # YouTube audience data (demographics) requires YouTube Analytics API and OAuth.
        # Returning None for MVP public data.
        return None

    async def refresh_token(
        self,
        connection: PlatformConnection,
    ) -> Tuple[str, Optional[str], Optional[datetime]]:
        # Not needed for Public API key.
        return connection.access_token, connection.refresh_token, connection.token_expires_at

    async def revoke_token(
        self,
        connection: PlatformConnection,
    ) -> bool:
        return True
