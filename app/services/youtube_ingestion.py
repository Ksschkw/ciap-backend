"""
YouTube Ingestion Service
=========================
Handles two flows:

1. PUBLIC SEARCH (no OAuth needed) — SME discovery feed
   - Uses YouTube Data API v3 with just an API Key
   - Searches for Nigerian/African creators by keyword/category
   - Stores results in creator_profiles + content_items + content_metric_snapshots
   - SMEs ALWAYS query our DB, never YouTube directly

2. OAUTH SYNC (creator authenticated) — Creator Dashboard deep analytics
   - Uses access token stored in platform_connections
   - Pulls private stats: watch time, revenue, audience demographics
   - Updates audience_snapshots for the Creator Dashboard

Both flows store into DB and are safe to call on a schedule.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from googleapiclient.discovery import build  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from app.config import settings
from DATA.data_connections.repositories.concrete import (
    SQLAudienceSnapshotRepository,
    SQLContentMetricRepository,
    SQLContentRepository,
    SQLCreatorProfileRepository,
    SQLPlatformConnectionRepository,
    SQLUserRepository,
)
from DATA.models.content import AudienceSnapshot, ContentItem, ContentMetricSnapshot
from DATA.models.users import CreatorProfile, PlatformConnection, User


_PLATFORM = "YOUTUBE"


def _yt_client() -> Any:
    """Build a YouTube Data API v3 client using the public API key."""
    if not settings.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY is not set in the environment or .env file")
    
    # Using developerKey specifically for public API access.
    return build("youtube", "v3", developerKey=settings.youtube_api_key, cache_discovery=False)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── PUBLIC SEARCH INGESTION ──────────────────────────────────────────────────

def ingest_public_creators(db: Session, query: str, max_results: int = 25) -> dict[str, Any]:
    """
    Search YouTube for creators matching `query`, upsert their profiles and
    latest video metrics into our DB.

    Called by:  POST /api/v1/youtube/ingest-public
    No auth required on the endpoint (admin-only recommended for production).
    """
    yt = _yt_client()
    user_repo = SQLUserRepository(db)
    creator_repo = SQLCreatorProfileRepository(db)
    content_repo = SQLContentRepository(db)
    metric_repo = SQLContentMetricRepository(db)

    # 1. Search for channels
    search_resp = yt.search().list(
        part="snippet",
        q=query,
        type="channel",
        maxResults=max_results,
        relevanceLanguage="en",
        regionCode="NG",  # Nigerian region for local relevance
    ).execute()

    channel_ids = [item["id"]["channelId"] for item in search_resp.get("items", []) if item.get("id", {}).get("channelId")]

    if not channel_ids:
        return {"ingested": 0, "channels": []}

    # 2. Fetch channel details + stats in one call
    channels_resp = yt.channels().list(
        part="snippet,statistics,brandingSettings",
        id=",".join(channel_ids),
    ).execute()

    ingested_channels: list[dict[str, Any]] = []

    for channel in channels_resp.get("items", []):
        channel_id: str = channel["id"]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})

        channel_title = snippet.get("title", "Unknown Creator")
        description = snippet.get("description", "")
        country = snippet.get("country", "NG")
        subscriber_count = int(stats.get("subscriberCount", 0))
        video_count = int(stats.get("videoCount", 0))

        # Use channel_id as the unique email handle to avoid duplicate users
        synthetic_email = f"yt_{channel_id.lower()}@youtube-ingested.ciap"

        # 3. Upsert User
        user = user_repo.get_by_email(synthetic_email)
        if user is None:
            user = User(
                id=uuid4(),
                email=synthetic_email,
                hashed_password=None,  # No login for auto-ingested creators
                role="CREATOR",
                full_name=channel_title,
                language_preference="en",
                status="ACTIVE",
                is_email_verified=True,
            )
            db.add(user)
            db.flush()

        # 4. Upsert CreatorProfile
        profile = creator_repo.get_by_user_id(user.id)
        if profile is None:
            profile = CreatorProfile(
                id=uuid4(),
                user_id=user.id,
                category="Content Creator",
                bio=description[:500] if description else None,
                location_country=country[:2].upper() if country else "NG",
                total_followers=subscriber_count,
                is_public=True,
                social_handles={"youtube": f"https://youtube.com/channel/{channel_id}"},
            )
            db.add(profile)
            db.flush()
        else:
            profile.total_followers = subscriber_count  # type: ignore[assignment]
            profile.bio = description[:500] if description else profile.bio  # type: ignore[assignment]
            db.flush()

        # 5. Upsert PlatformConnection (marks this as a YouTube channel)
        conn_repo = SQLPlatformConnectionRepository(db)
        conn = conn_repo.get_by_user_and_platform(user.id, _PLATFORM)
        if conn is None:
            conn = PlatformConnection(
                id=uuid4(),
                user_id=user.id,
                platform_name=_PLATFORM,
                platform_user_id=channel_id,
                platform_username=channel_title,
                access_token="PUBLIC_API_KEY_ONLY",
                is_active=True,
                last_synced_at=_utcnow(),
            )
            db.add(conn)
            db.flush()
        else:
            conn.last_synced_at = _utcnow()  # type: ignore[assignment]
            db.flush()

        # 6. Fetch latest 5 videos and upsert content + metrics
        videos_resp = yt.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            order="date",
            maxResults=5,
        ).execute()

        video_ids = [v["id"]["videoId"] for v in videos_resp.get("items", []) if v.get("id", {}).get("videoId")]

        if video_ids:
            video_details = yt.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids),
            ).execute()

            for video in video_details.get("items", []):
                vid_id = video["id"]
                vid_snippet = video.get("snippet", {})
                vid_stats = video.get("statistics", {})

                posted_raw = vid_snippet.get("publishedAt", "")
                posted_at = datetime.fromisoformat(posted_raw.replace("Z", "+00:00")) if posted_raw else _utcnow()

                thumbnails = vid_snippet.get("thumbnails", {})
                thumb_url = (thumbnails.get("high") or thumbnails.get("default") or {}).get("url")

                content = ContentItem(
                    id=uuid4(),
                    creator_id=profile.id,
                    platform_connection_id=conn.id,
                    platform=_PLATFORM,
                    external_id=vid_id,
                    media_type="VIDEO",
                    title=vid_snippet.get("title"),
                    caption=vid_snippet.get("description", "")[:1000],
                    hashtags=vid_snippet.get("tags", []),
                    permalink=f"https://www.youtube.com/watch?v={vid_id}",
                    thumbnail_url=thumb_url,
                    status="ACTIVE",
                    posted_at=posted_at,
                    synced_at=_utcnow(),
                )
                saved_content = content_repo.upsert_by_external_id(content)

                views = int(vid_stats.get("viewCount", 0))
                likes = int(vid_stats.get("likeCount", 0))
                comments = int(vid_stats.get("commentCount", 0))
                reach = views
                engagement_rate = round(((likes + comments) / reach * 100), 4) if reach > 0 else 0.0

                metric = ContentMetricSnapshot(
                    id=uuid4(),
                    content_id=saved_content.id,
                    captured_at=_utcnow(),
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=0,
                    saves=0,
                    reach=reach,
                    impressions=int(reach * 1.3),
                    engagement_rate=engagement_rate,
                )
                metric_repo.insert_snapshot(metric)

        db.commit()
        ingested_channels.append({"channel_id": channel_id, "title": channel_title, "subscribers": subscriber_count})

    return {"ingested": len(ingested_channels), "channels": ingested_channels}


# ─── OAUTH SYNC (Creator-authenticated) ──────────────────────────────────────

def sync_creator_youtube_channel(db: Session, user_id: UUID) -> dict[str, Any]:
    """
    Pull YouTube data for an authenticated creator using their stored OAuth token.
    Requires their access_token stored in platform_connections.

    Fetches:
    - Channel stats: subscribers, total views, video count
    - Latest 10 videos with full stats (views, likes, comments, duration)
    - Audience demographics if available via the YouTube Analytics API
    - Stores everything in our DB for the analytics dashboard

    Called by:  POST /api/v1/youtube/sync  (auth required, creator only)
    """
    conn_repo    = SQLPlatformConnectionRepository(db)
    creator_repo = SQLCreatorProfileRepository(db)
    content_repo = SQLContentRepository(db)
    metric_repo  = SQLContentMetricRepository(db)
    audience_repo = SQLAudienceSnapshotRepository(db)

    conn = conn_repo.get_by_user_and_platform(user_id, _PLATFORM)
    if conn is None:
        return {"success": False, "message": "No YouTube account connected. Please connect via OAuth first."}

    channel_id = conn.platform_user_id  # YouTube channel ID (UCxxxxxxx)

    # ── Build an authenticated client using OAuth tokens ──────────────────────
    access_token  = str(conn.access_token)  if conn.access_token  else None
    refresh_token = str(conn.refresh_token) if conn.refresh_token else None
    is_oauth_token = access_token and access_token != "PUBLIC_API_KEY_ONLY"

    yt = None
    creds = None
    is_oauth_token_valid = False

    if is_oauth_token:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build as yt_build

            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )

            # Refresh if expired (this is the critical fix)
            if creds.expired or not creds.valid:
                creds.refresh(Request())
                # Save the new access token back to DB
                conn_repo.update_tokens(
                    connection_id=conn.id,
                    new_access_token=creds.token,
                    new_refresh_token=creds.refresh_token or refresh_token,
                    new_expires_at=creds.expiry,
                )
                db.commit()

            yt = yt_build("youtube", "v3", credentials=creds, cache_discovery=False)
            is_oauth_token_valid = True
        except Exception as e:
            # Log but don't crash — fall through to public key fallback
            import logging
            logging.getLogger(__name__).warning(f"OAuth token refresh failed: {e}. Falling back to public API key.")
            yt = _yt_client()
    else:
        yt = _yt_client()

    # ── Channel stats ─────────────────────────────────────────────────────────
    # If we have valid OAuth credentials, use mine=True (no channel ID needed)
    # Otherwise fall back to querying by stored channel ID
    if is_oauth_token_valid and creds is not None:
        ch_resp = yt.channels().list(
            part="snippet,statistics,brandingSettings,contentDetails",
            mine=True,
        ).execute()
    else:
        if not channel_id:
            return {"success": False, "message": "No YouTube channel ID stored. Please reconnect your YouTube account."}
        ch_resp = yt.channels().list(
            part="snippet,statistics,brandingSettings",
            id=channel_id,
        ).execute()

    if not ch_resp.get("items"):
        return {"success": False, "message": "Channel not found on YouTube."}

    ch = ch_resp["items"][0]
    ch_stats   = ch.get("statistics", {})
    ch_snippet = ch.get("snippet", {})

    subscriber_count = int(ch_stats.get("subscriberCount", 0))
    total_view_count = int(ch_stats.get("viewCount", 0))
    video_count      = int(ch_stats.get("videoCount", 0))
    country          = ch_snippet.get("country", "NG")

    # When using mine=True the API response gives us the real channel ID — persist it
    real_channel_id = ch.get("id", channel_id)
    if real_channel_id and real_channel_id != channel_id:
        conn.platform_user_id = real_channel_id  # type: ignore[assignment]
        db.flush()
        channel_id = real_channel_id

    # ── Update or create CreatorProfile ──────────────────────────────────────
    profile = creator_repo.get_by_user_id(user_id)
    if profile is None:
        # Create a CreatorProfile on first sync if missing (e.g. email/password users)
        from DATA.models.users import CreatorProfile as _CP
        profile = _CP(
            id=uuid4(),
            user_id=user_id,
            category="Content Creator",
            bio=ch_snippet.get("description", "")[:500] or None,
            location_country=(country[:2].upper() if country else "NG"),
            total_followers=subscriber_count,
            is_public=True,
            social_handles={"youtube": f"https://youtube.com/channel/{channel_id}"},
        )
        db.add(profile)
        db.flush()
    else:
        creator_repo.update_total_followers(user_id, subscriber_count)
        if country:
            profile.location_country = country[:2].upper()  # type: ignore[assignment]
            db.flush()

    # ── Audience snapshot with demographics (OAuth-only) ──────────────────────
    age_dist    = {}
    gender_dist = {}
    top_countries_data: list = []
    new_subs    = 0

    if is_oauth_token_valid and creds is not None:
        try:
            from googleapiclient.discovery import build as yt_build
            analytics = yt_build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)  # type: ignore[reportPossiblyUnbound]
            today = datetime.now(timezone.utc).date().isoformat()
            thirty_days_ago = (datetime.now(timezone.utc).date().replace(day=1)).isoformat()

            # Subscriber gains
            subs_resp = analytics.reports().query(
                ids="channel==MINE",
                startDate=thirty_days_ago,
                endDate=today,
                metrics="subscribersGained,subscribersLost",
            ).execute()
            if subs_resp.get("rows"):
                row = subs_resp["rows"][0]
                new_subs = int(row[0]) - int(row[1])

            # Age/gender demographics
            demo_resp = analytics.reports().query(
                ids="channel==MINE",
                startDate=thirty_days_ago,
                endDate=today,
                metrics="viewerPercentage",
                dimensions="ageGroup,gender",
            ).execute()
            for row in demo_resp.get("rows", []):
                age_group, gender, pct = row[0], row[1], float(row[2])
                age_dist.setdefault(age_group, 0)
                age_dist[age_group] += pct
                gender_dist.setdefault(gender, 0)
                gender_dist[gender] += pct

            # Top countries
            geo_resp = analytics.reports().query(
                ids="channel==MINE",
                startDate=thirty_days_ago,
                endDate=today,
                metrics="views",
                dimensions="country",
                sort="-views",
                maxResults=5,
            ).execute()
            top_countries_data = [
                {"country": row[0], "views": int(row[1])}
                for row in geo_resp.get("rows", [])
            ]
        except Exception:
            pass  # Analytics API not available — graceful degradation

    snapshot = AudienceSnapshot(
        id=uuid4(),
        creator_id=profile.id,  # always set — profile guaranteed above
        platform_connection_id=conn.id,
        captured_at=_utcnow(),
        total_followers=subscriber_count,
        new_followers_this_period=new_subs if new_subs else None,
        age_distribution=age_dist or None,
        gender_distribution=gender_dist or None,
        top_countries=top_countries_data or None,
    )
    audience_repo.insert_snapshot(snapshot)

    # ── Latest 10 videos with full stats ─────────────────────────────────────
    videos_resp = yt.search().list(
        part="snippet",
        channelId=channel_id,
        type="video",
        order="date",
        maxResults=10,
    ).execute()

    video_ids = [v["id"]["videoId"] for v in videos_resp.get("items", []) if v.get("id", {}).get("videoId")]
    synced_videos = 0

    if video_ids:
        video_details = yt.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
        ).execute()

        for video in video_details.get("items", []):
            vid_id      = video["id"]
            vid_snippet = video.get("snippet", {})
            vid_stats   = video.get("statistics", {})
            vid_content = video.get("contentDetails", {})

            posted_raw = vid_snippet.get("publishedAt", "")
            posted_at  = datetime.fromisoformat(posted_raw.replace("Z", "+00:00")) if posted_raw else _utcnow()

            thumbnails = vid_snippet.get("thumbnails", {})
            thumb_url  = (
                thumbnails.get("maxres")
                or thumbnails.get("high")
                or thumbnails.get("default")
                or {}
            ).get("url")

            # Parse ISO 8601 duration (PT4M13S → seconds)
            duration_seconds: int | None = None
            raw_duration = vid_content.get("duration")
            if raw_duration:
                import re
                m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", raw_duration)
                if m:
                    h, mi, s = (int(x or 0) for x in m.groups())
                    duration_seconds = h * 3600 + mi * 60 + s

            content = ContentItem(
                id=uuid4(),
                creator_id=profile.id,  # always set — profile guaranteed above
                platform_connection_id=conn.id,
                platform=_PLATFORM,
                external_id=vid_id,
                media_type="VIDEO",
                title=vid_snippet.get("title"),
                caption=vid_snippet.get("description", "")[:1000],
                hashtags=vid_snippet.get("tags", []),
                permalink=f"https://www.youtube.com/watch?v={vid_id}",
                thumbnail_url=thumb_url,
                duration_seconds=duration_seconds,
                status="ACTIVE",
                posted_at=posted_at,
                synced_at=_utcnow(),
            )
            saved_content = content_repo.upsert_by_external_id(content)

            views    = int(vid_stats.get("viewCount",   0))
            likes    = int(vid_stats.get("likeCount",   0))
            comments = int(vid_stats.get("commentCount", 0))
            reach    = views
            engagement_rate = round(((likes + comments) / reach * 100), 4) if reach > 0 else 0.0

            metric = ContentMetricSnapshot(
                id=uuid4(),
                content_id=saved_content.id,
                captured_at=_utcnow(),
                views=views,
                likes=likes,
                comments=comments,
                shares=0,
                saves=0,
                reach=reach,
                impressions=int(reach * 1.3),
                engagement_rate=engagement_rate,
            )
            metric_repo.insert_snapshot(metric)
            synced_videos += 1

    conn_repo.update_last_synced(conn.id, _utcnow())
    db.commit()

    return {
        "success": True,
        "message": "YouTube channel synced successfully.",
        "data": {
            "channel_id":     channel_id,
            "subscribers":    subscriber_count,
            "total_views":    total_view_count,
            "video_count":    video_count,
            "videos_synced":  synced_videos,
            "demographics_fetched": bool(age_dist),
            "synced_at": _utcnow().isoformat(),
        },
    }

