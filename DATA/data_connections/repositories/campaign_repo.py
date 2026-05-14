"""
Campaign, Scoring, System Domain Repositories
===============================================
Covers:
    Campaign                 → ICampaignRepository
    CampaignCollaboration    → ICollaborationRepository
    CampaignCreatorBrief     → IBriefRepository
    ConversionEvent          → IConversionEventRepository
    InfluenceScore           → IInfluenceScoreRepository
    AuditLog                 → IAuditLogRepository
    Notification             → INotificationRepository

Matches ERD tables:
    campaigns                    → ICampaignRepository
    campaign_collaborations      → ICollaborationRepository
    campaign_creator_briefs      → IBriefRepository
    conversion_events            → IConversionEventRepository
    influence_scores             → IInfluenceScoreRepository
    audit_logs                   → IAuditLogRepository
    notifications                → INotificationRepository
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from DATA.data_connections.repositories.base import IRepository
from DATA.schemas.entities.campaign import (
    Campaign,
    CampaignCollaboration,
    CampaignCreatorBrief,
    ConversionEvent,
)
from DATA.schemas.entities.scoring import InfluenceScore
from DATA.schemas.entities.audit import AuditLog, Notification


# ══════════════════════════════════════════════════════════════════════════════
# ICampaignRepository — campaigns table
# ══════════════════════════════════════════════════════════════════════════════

class ICampaignRepository(IRepository[Campaign]):
    """CRUD contract for the `campaigns` table."""

    @abstractmethod
    def get_by_owner(self, sme_id: UUID, limit: int = 20, offset: int = 0) -> List[Campaign]:
        """Return campaigns owned by a user, newest first."""
        ...

    @abstractmethod
    def search(
        self,
        target_platforms: Optional[List[str]] = None,
        target_categories: Optional[List[str]] = None,
        target_locations: Optional[List[str]] = None,
        min_budget: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Campaign]:
        """
        Creator-facing discovery. Creators can browse open campaigns
        that match their platform/niche/location.
        Only returns status=ACTIVE campaigns.
        """
        ...

    @abstractmethod
    def update_status(self, campaign_id: UUID, status: str) -> Campaign:
        """
        Lifecycle transition. Valid transitions are enforced at service layer:
            DRAFT → ACTIVE → PAUSED → COMPLETED
            Any status → CANCELLED
        """
        ...

    @abstractmethod
    def update_spent_budget(
        self, campaign_id: UUID, additional_spend: Decimal
    ) -> None:
        """
        Increment spent_budget_ngn by additional_spend.
        Called by the payment service each time a collaboration is paid out.
        Uses SQL: UPDATE campaigns SET spent_budget_ngn = spent_budget_ngn + :amount
        to avoid race conditions.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# ICollaborationRepository — campaign_collaborations table
# ══════════════════════════════════════════════════════════════════════════════

class ICollaborationRepository(IRepository[CampaignCollaboration]):
    """
    CRUD contract for `campaign_collaborations`.

    A CampaignCollaboration links one Creator to one Campaign.
    It tracks the status lifecycle from INVITED → ... → COMPLETED.
    """

    @abstractmethod
    def get_by_campaign(
        self,
        campaign_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CampaignCollaboration]:
        """
        Return all collaborations under a campaign for an SME to review.
        Optional status filter for workflow management.
        """
        ...

    @abstractmethod
    def get_by_creator(
        self,
        creator_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[CampaignCollaboration]:
        """
        Return all campaigns a creator has been invited to or is participating in.
        Powers the creator's "My Campaigns" view.
        """
        ...

    @abstractmethod
    def get_by_tracking_code(self, tracking_code: str) -> Optional[CampaignCollaboration]:
        """
        Used by the conversion webhook to resolve which collaboration
        triggered a click/signup/purchase.
        tracking_code is a unique short code per collaboration.
        """
        ...

    @abstractmethod
    def update_status(
        self,
        collaboration_id: UUID,
        status: str,
        timestamp_field: Optional[str] = None,
    ) -> CampaignCollaboration:
        """
        Advance the collaboration lifecycle.
        timestamp_field can be 'responded_at' or 'completed_at'
        to automatically stamp the correct datetime alongside the status change.
        """
        ...

    @abstractmethod
    def link_content(
        self, collaboration_id: UUID, content_id: UUID
    ) -> CampaignCollaboration:
        """
        Called when a creator submits their deliverable post.
        Sets content_id FK and advances status to CONTENT_SUBMITTED.
        """
        ...

    @abstractmethod
    def increment_conversion_counters(
        self,
        collaboration_id: UUID,
        clicks_delta: int = 0,
        conversions_delta: int = 0,
    ) -> None:
        """
        Atomically increment total_clicks and/or total_conversions.
        Called by ConversionEvent processing.
        Uses SQL UPDATE ... SET total_clicks = total_clicks + :delta
        to be safe under concurrent webhook delivery.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IBriefRepository — campaign_creator_briefs table
# ══════════════════════════════════════════════════════════════════════════════

class IBriefRepository(IRepository[CampaignCreatorBrief]):
    """
    CRUD contract for `campaign_creator_briefs`.

    A brief is 1-to-1 with a CampaignCollaboration.
    Created by an SME when they invite a creator.
    """

    @abstractmethod
    def get_by_collaboration(
        self, collaboration_id: UUID
    ) -> Optional[CampaignCreatorBrief]:
        """
        Return the brief for a specific collaboration.
        Used when a creator views their campaign requirements.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IConversionEventRepository — conversion_events table
# ══════════════════════════════════════════════════════════════════════════════

class IConversionEventRepository(IRepository[ConversionEvent]):
    """
    CRUD contract for `conversion_events`.

    Conversion events are created by the webhook endpoint when an SME's
    tracking URL is hit (click, signup, purchase, etc.).
    This table is effectively APPEND-ONLY — events are never updated.
    """

    @abstractmethod
    def get_by_collaboration(
        self,
        collaboration_id: UUID,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[ConversionEvent]:
        """
        Return all conversion events for a collaboration.
        Used to build the ROI breakdown on an SME's campaign dashboard.
        """
        ...

    @abstractmethod
    def get_by_tracking_code(
        self, tracking_code: str, session_id: Optional[str] = None
    ) -> List[ConversionEvent]:
        """
        Used for deduplication — check if this session_id already has an
        event for this tracking_code before inserting a duplicate.
        """
        ...

    @abstractmethod
    def insert_event(self, event: ConversionEvent) -> ConversionEvent:
        """
        Primary write operation. Always inserts — never mutates existing events.
        After inserting, the service should call
        ICollaborationRepository.increment_conversion_counters().
        """
        ...

    @abstractmethod
    def get_revenue_summary(self, collaboration_id: UUID) -> Dict[str, Any]:
        """
        Aggregate total revenue from PURCHASE events for a collaboration.
        Returns: { 'total_revenue_ngn': Decimal, 'purchase_count': int }
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IInfluenceScoreRepository — influence_scores table
# ══════════════════════════════════════════════════════════════════════════════

class IInfluenceScoreRepository(IRepository[InfluenceScore]):
    """
    CRUD contract for `influence_scores`.

    APPEND-ONLY. Every weekly ML scoring run inserts a new row 
    rather than updating the previous one. This gives us a full
    history of how a creator's score has changed over time.
    """

    @abstractmethod
    def get_latest_for_creator(self, creator_id: UUID) -> Optional[InfluenceScore]:
        """
        Return the most recent score for a creator.
        ORDER BY scored_at DESC LIMIT 1.
        Used by the dashboard and SME discovery to show current score.
        """
        ...

    @abstractmethod
    def get_history_for_creator(
        self,
        creator_id: UUID,
        limit: int = 52,  # one year of weekly scores
    ) -> List[InfluenceScore]:
        """
        Return the score history for a creator, newest first.
        Used to plot the score trend chart on the creator dashboard.
        """
        ...

    @abstractmethod
    def insert_score(self, score: InfluenceScore) -> InfluenceScore:
        """
        Main write. After inserting, the ML service must also call
        ICreatorProfileRepository.update_influence_score() to keep
        CreatorProfile.influence_score denormalised and fresh for fast reads.
        """
        ...

    @abstractmethod
    def get_top_creators(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 20,
    ) -> List[InfluenceScore]:
        """
        Leaderboard query — returns the latest score per creator,
        sorted by score DESC, filtered by category/location if given.
        Used for SME leaderboard and creator discovery ranking.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# INotificationRepository — notifications table
# ══════════════════════════════════════════════════════════════════════════════

class INotificationRepository(IRepository[Notification]):
    """
    CRUD contract for `notifications`.

    Notifications are lightweight system messages sent to a user's inbox.
    Examples: CAMPAIGN_INVITE, PAYMENT_RECEIVED, SCORE_UPDATED.
    """

    @abstractmethod
    def get_for_user(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Return notifications for a user, newest first.
        If unread_only=True, filter by is_read=False.
        """
        ...

    @abstractmethod
    def mark_read(self, notification_id: UUID) -> None:
        """Set is_read=True and read_at=now() for a notification."""
        ...

    @abstractmethod
    def mark_all_read(self, user_id: UUID) -> int:
        """
        Bulk mark all unread notifications as read for a user.
        Returns the count of notifications that were updated.
        """
        ...

    @abstractmethod
    def get_unread_count(self, user_id: UUID) -> int:
        """
        Efficient COUNT query for the notification bell badge.
        SELECT COUNT(*) FROM notifications WHERE user_id=:id AND is_read=False.
        """
        ...


# ══════════════════════════════════════════════════════════════════════════════
# IAuditLogRepository — audit_logs table
# ══════════════════════════════════════════════════════════════════════════════

class IAuditLogRepository(IRepository[AuditLog]):
    """
    CRUD contract for `audit_logs`.

    APPEND-ONLY, IMMUTABLE. Once written, audit log rows are NEVER updated
    or deleted. No update() method is meaningful here — only insert and query.

    Standard actions to log (call insert_log from any service):
        PLATFORM_CONNECTED, PLATFORM_DISCONNECTED,
        INGESTION_COMPLETED, INGESTION_FAILED,
        CAMPAIGN_CREATED, CAMPAIGN_STATUS_CHANGED,
        COLLABORATION_INVITED, COLLABORATION_ACCEPTED,
        SCORE_CALCULATED, PAYMENT_PROCESSED
    """

    @abstractmethod
    def insert_log(self, log: AuditLog) -> AuditLog:
        """
        Primary write — always INSERT, never UPDATE.
        Call this from services after every significant action.

        Example (inside a service method):
            log = AuditLog(
                user_id=current_user.id,
                action="CAMPAIGN_CREATED",
                entity_type="Campaign",
                entity_id=new_campaign.id,
                metadata_json={"name": new_campaign.name},
                ip_address=request.client.host,
            )
            audit_repo.insert_log(log)
        """
        ...

    @abstractmethod
    def get_by_user(
        self,
        user_id: UUID,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Return all audit logs for a user. Supports optional action filter.
        Used in the admin panel for user activity review.
        """
        ...

    @abstractmethod
    def get_by_entity(
        self, entity_type: str, entity_id: UUID
    ) -> List[AuditLog]:
        """
        Return all audit events touching a specific record.
        Example: get_by_entity("Campaign", campaign_id) shows every
        status change, budget update, and collaboration linked to that campaign.
        """
        ...