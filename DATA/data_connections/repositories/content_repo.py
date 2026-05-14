"""
Content Domain Repositories
============================
Covers: ContentItem, ContentMetricSnapshot, AudienceSnapshot

Matches ERD tables:
    content_items              → IContentRepository
    content_metric_snapshots   → IContentMetricRepository
    audience_snapshots         → IAudienceSnapshotRepository

These are the core tables populated by the data ingestion service every sync.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from DATA.data_connections.repositories.base import IRepository
from DATA.schemas.entities.content import AudienceSnapshot, ContentItem, ContentMetricSnapshot


# ══════════════════════════════════════════════════════════════════════════════
# IContentRepository — content_items table
# ══════════════════════════════════════════════════════════════════════════════

class IContentRepository(IRepository[ContentItem]):
    """
    CRUD contract for the `content_items` table.
    Content items are fetched from external APIs and normalised before storage.
    """

    @abstractmethod
    def get_by_external_id(self, external_id: str) -> Optional[ContentItem]:
        """
        Lookup by the platform-native post/video ID.
        Used during ingestion to check if a content item already exists
        before deciding to INSERT vs UPDATE.

        Example: YouTube videoId='dQw4w9WgXcQ'
        """
        ...

    @abstractmethod
    def get_by_creator(
        self,
        creator_id: UUID,
        platform: Optional[str] = None,
        media_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ContentItem]:
        """
        Return all content items for a creator, with optional platform/type filters.
        Used by the /content endpoint and creator dashboard.
        Powers the Week 2 GET /content deliverable.
        """
        ...

    @abstractmethod
    def get_by_platform_connection(
        self, platform_connection_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ContentItem]:
        """
        Return items sourced from a specific platform connection.
        Used by the ingestion service to know what's already synced.
        """
        ...

    @abstractmethod
    def upsert(self, item: ContentItem) -> ContentItem:
        """
        Insert if external_id doesn't exist, update metadata if it does.
        This is the primary write operation during data ingestion.

        Note: This does NOT update metrics — metrics go in ContentMetricSnapshot.
        """
        ...

    @abstractmethod
    def soft_delete(self, content_id: UUID) -> None:
        """
        Set status='DELETED' instead of hard deleting.
        Called when the ingestion service detects a post was removed on the platform.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IContentMetricRepository — content_metric_snapshots table
# ══════════════════════════════════════════════════════════════════════════════

class IContentMetricRepository(IRepository[ContentMetricSnapshot]):
    """
    CRUD contract for `content_metric_snapshots`.

    This table is APPEND-ONLY — we never UPDATE a metric snapshot.
    Every ingestion run creates a NEW snapshot row.
    This gives us a historical time-series of each content piece's performance.
    """

    @abstractmethod
    def get_latest_for_content(self, content_id: UUID) -> Optional[ContentMetricSnapshot]:
        """
        Return the most recent snapshot for a given ContentItem.
        Used by the dashboard to show current stats.
        ORDER BY captured_at DESC LIMIT 1.
        """
        ...

    @abstractmethod
    def get_history_for_content(
        self,
        content_id: UUID,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[ContentMetricSnapshot]:
        """
        Return all snapshots for a content item within an optional date range.
        Used to build time-series charts in the creator dashboard.
        """
        ...

    @abstractmethod
    def get_aggregated_for_creator(self, creator_id: UUID) -> dict:
        """
        Return SUM of views, likes, comments across ALL content items for a creator.
        Used by the /dashboard endpoint.

        Returns a dict:
            {
                'total_views': int,
                'total_likes': int,
                'total_comments': int,
                'total_shares': int,
                'total_reach': int,
                'avg_engagement_rate': float
            }
        """
        ...

    @abstractmethod
    def insert_snapshot(self, snapshot: ContentMetricSnapshot) -> ContentMetricSnapshot:
        """
        The main write operation. Always adds a new row — never updates.
        Called at the end of each ingestion sync per content item.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IAudienceSnapshotRepository — audience_snapshots table
# ══════════════════════════════════════════════════════════════════════════════

class IAudienceSnapshotRepository(IRepository[AudienceSnapshot]):
    """
    CRUD contract for `audience_snapshots`.
    Also APPEND-ONLY — taken weekly per platform connection.
    Contains demographic breakdowns (age, gender, country, city, language).
    """

    @abstractmethod
    def get_latest_for_creator(
        self, creator_id: UUID, platform: Optional[str] = None
    ) -> Optional[AudienceSnapshot]:
        """
        Return the most recent audience snapshot for a creator.
        If platform is specified, filter by platform_connection.platform_name.
        """
        ...

    @abstractmethod
    def get_history_for_creator(
        self,
        creator_id: UUID,
        since: Optional[datetime] = None,
    ) -> List[AudienceSnapshot]:
        """
        Return all audience snapshots for a creator, sorted by captured_at ASC.
        Used to show follower growth over time on the dashboard.
        """
        ...

    @abstractmethod
    def insert_snapshot(self, snapshot: AudienceSnapshot) -> AudienceSnapshot:
        """
        The main write operation. Always inserts a new row — never updates.
        Called weekly per creator per active platform connection.
        """
        ...