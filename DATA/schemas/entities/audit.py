"""
Audit logging and notification entity models.

Tables covered:
    AuditLog        - Immutable record of every significant system action
    Notification    - In-app notification for creators and SMEs
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AuditAction(str, enum.Enum):
    """
    Typed vocabulary of all loggable system events.
    Using an enum (not free-text) makes querying and alerting reliable.
    """
    # Auth
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"

    # OAuth / Platform connections
    PLATFORM_CONNECTED = "PLATFORM_CONNECTED"
    PLATFORM_DISCONNECTED = "PLATFORM_DISCONNECTED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED"

    # Data ingestion
    INGESTION_STARTED = "INGESTION_STARTED"
    INGESTION_COMPLETED = "INGESTION_COMPLETED"
    INGESTION_FAILED = "INGESTION_FAILED"
    CONTENT_ITEM_CREATED = "CONTENT_ITEM_CREATED"
    METRIC_SNAPSHOT_CREATED = "METRIC_SNAPSHOT_CREATED"
    AUDIENCE_SNAPSHOT_CREATED = "AUDIENCE_SNAPSHOT_CREATED"

    # Campaigns
    CAMPAIGN_CREATED = "CAMPAIGN_CREATED"
    CAMPAIGN_UPDATED = "CAMPAIGN_UPDATED"
    CAMPAIGN_CANCELLED = "CAMPAIGN_CANCELLED"
    COLLABORATION_INVITED = "COLLABORATION_INVITED"
    COLLABORATION_ACCEPTED = "COLLABORATION_ACCEPTED"
    COLLABORATION_DECLINED = "COLLABORATION_DECLINED"
    COLLABORATION_COMPLETED = "COLLABORATION_COMPLETED"
    BRIEF_SENT = "BRIEF_SENT"
    CONTENT_SUBMITTED = "CONTENT_SUBMITTED"
    CONTENT_APPROVED = "CONTENT_APPROVED"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"

    # ML / Scoring
    INFLUENCE_SCORE_UPDATED = "INFLUENCE_SCORE_UPDATED"

    # Admin
    ADMIN_ACTION = "ADMIN_ACTION"
    DATA_EXPORT = "DATA_EXPORT"


class NotificationType(str, enum.Enum):
    """Category of in-app notification to drive icon/colour in the frontend."""
    CAMPAIGN_INVITE = "CAMPAIGN_INVITE"
    CAMPAIGN_UPDATE = "CAMPAIGN_UPDATE"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    CONTENT_APPROVED = "CONTENT_APPROVED"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    SCORE_UPDATED = "SCORE_UPDATED"
    DATA_SYNCED = "DATA_SYNCED"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    GENERAL = "GENERAL"


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(BaseModel):
    """
    Immutable append-only record of every significant event in the system.
    Used for debugging, compliance, and anomaly detection.
    NEVER UPDATE or DELETE rows in this table.

    Backend maps this to the `audit_logs` table.

    Indexes:
        - user_id + created_at DESC
        - action
        - created_at DESC

    Partitioning:
        Partition by range on created_at (monthly) for long-term retention.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: Optional[UUID] = Field(
        None, description="FK → users.id. NULL for system-initiated actions."
    )
    action: AuditAction = Field(..., description="Typed event name.")
    entity_type: Optional[str] = Field(
        None,
        description="The model type that was affected, e.g. 'Campaign', 'ContentItem'.",
    )
    entity_id: Optional[UUID] = Field(
        None, description="ID of the affected entity, if applicable."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Arbitrary JSON payload with request context. "
            "e.g. {'platform': 'YOUTUBE', 'videos_ingested': 12, 'ip': '...'}"
        ),
    )
    ip_address: Optional[str] = Field(None, description="Requester IP for security audit.")
    user_agent: Optional[str] = Field(None, description="Browser/client user agent string.")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Immutable — never updated.",
    )


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(BaseModel):
    """
    In-app notification for creators and SMEs.
    Created by backend services and consumed by the frontend via SSE or polling.

    Backend maps this to the `notifications` table.

    Indexes:
        - user_id + is_read + created_at DESC (primary read pattern)
        - created_at DESC
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="FK → users.id — who receives this notification.")
    notification_type: NotificationType = Field(...)
    title: str = Field(..., max_length=120)
    body: str = Field(..., max_length=500)

    # --- Deep-link so frontend can route to the right page on click ---
    action_url: Optional[str] = Field(
        None,
        description="Relative frontend route, e.g. '/campaigns/uuid' or '/dashboard'.",
    )
    related_entity_id: Optional[UUID] = Field(
        None,
        description="ID of the Campaign, Collaboration, etc. that triggered this notification.",
    )

    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)