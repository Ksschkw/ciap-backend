"""
Campaign and collaboration entity models.

Maps 1-to-1 with PostgreSQL tables defined in schema_erd.mmd.

Tables covered:
    Campaign                - An SME's marketing campaign
    CampaignCollaboration   - Links a specific creator to a campaign
    CampaignCreatorBrief    - The brief/requirements sent to a creator
    ConversionEvent         - Individual conversion tracked via UTM / webhook
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CampaignStatus(str, enum.Enum):
    """Lifecycle of an SME campaign."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CollaborationStatus(str, enum.Enum):
    """Status of a specific creator's participation in a campaign."""
    INVITED = "INVITED"          # SME sent invite, awaiting creator response
    ACCEPTED = "ACCEPTED"        # Creator accepted
    DECLINED = "DECLINED"        # Creator declined
    CONTENT_SUBMITTED = "CONTENT_SUBMITTED"  # Creator posted, linked in system
    APPROVED = "APPROVED"        # SME approved the content
    REJECTED = "REJECTED"        # SME rejected; creator can resubmit
    PAYMENT_PENDING = "PAYMENT_PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CampaignObjective(str, enum.Enum):
    """Marketing objective — drives ML scoring weights in Phase 2."""
    BRAND_AWARENESS = "BRAND_AWARENESS"
    LEAD_GENERATION = "LEAD_GENERATION"
    PRODUCT_SALES = "PRODUCT_SALES"
    APP_INSTALLS = "APP_INSTALLS"
    WEBSITE_TRAFFIC = "WEBSITE_TRAFFIC"
    CONTENT_CREATION = "CONTENT_CREATION"  # Just want content, no conversion goal
    COMMUNITY_GROWTH = "COMMUNITY_GROWTH"


class ConversionEventType(str, enum.Enum):
    """Types of user actions we can track as conversions."""
    CLICK = "CLICK"
    SIGNUP = "SIGNUP"
    PURCHASE = "PURCHASE"
    APP_INSTALL = "APP_INSTALL"
    FORM_SUBMIT = "FORM_SUBMIT"
    VIDEO_VIEW = "VIDEO_VIEW"   # Paid view tracking
    CUSTOM = "CUSTOM"


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

class Campaign(BaseModel):
    """
    An SME/Agency's marketing campaign. One campaign can involve
    multiple creators via CampaignCollaboration rows.

    Backend maps this to the `campaigns` table.

    Indexes:
        - sme_id + status
        - start_date, end_date (for active campaign queries)
        - created_at DESC
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    sme_id: UUID = Field(..., description="FK → sme_profiles.id")

    name: str = Field(..., min_length=2, max_length=200, description="Campaign name.")
    description: Optional[str] = Field(None, max_length=1000)
    objective: CampaignObjective = Field(..., description="Primary marketing goal.")

    # --- Budget ---
    total_budget_ngn: float = Field(..., ge=0, description="Total campaign budget in NGN.")
    spent_budget_ngn: float = Field(default=0.0, ge=0, description="Tracked spend so far.")

    # --- Timeline ---
    start_date: date = Field(..., description="Campaign start date.")
    end_date: date = Field(..., description="Campaign end date.")

    # --- Targeting criteria (stored for reference / ML training) ---
    target_platforms: List[str] = Field(
        default_factory=list,
        description="Platforms the campaign runs on, e.g. ['YOUTUBE', 'INSTAGRAM']",
    )
    target_categories: List[str] = Field(
        default_factory=list,
        description="Creator niches SME wants, e.g. ['Music', 'Lifestyle']",
    )
    target_locations: List[str] = Field(
        default_factory=list,
        description="Target audience locations, e.g. ['NG', 'GH']",
    )
    min_influence_score: Optional[float] = Field(
        None, ge=0.0, le=100.0,
        description="Minimum creator influence score for eligibility.",
    )
    min_followers: Optional[int] = Field(
        None, ge=0, description="Minimum follower count for eligibility."
    )

    status: CampaignStatus = Field(default=CampaignStatus.DRAFT)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# CampaignCollaboration
# ---------------------------------------------------------------------------

class CampaignCollaboration(BaseModel):
    """
    Joins a specific creator to a specific campaign.
    Tracks the full lifecycle from invitation to payment.

    Backend maps this to the `campaign_collaborations` table.

    Indexes:
        - campaign_id
        - creator_id
        - status
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    campaign_id: UUID = Field(..., description="FK → campaigns.id")
    creator_id: UUID = Field(..., description="FK → creator_profiles.id")
    content_id: Optional[UUID] = Field(
        None, description="FK → content_items.id. NULL until creator posts."
    )

    # --- Commercial terms ---
    negotiated_fee_ngn: Optional[float] = Field(
        None, ge=0, description="Agreed payment to creator in NGN."
    )
    payment_gateway_reference: Optional[str] = Field(
        None, description="Paystack/Flutterwave transaction reference for audit."
    )

    # --- Tracking ---
    tracking_link: Optional[str] = Field(
        None,
        description="UTM-tagged or short link assigned to this creator for this campaign.",
    )
    tracking_code: Optional[str] = Field(
        None, description="Short unique code for QR/offline tracking."
    )

    # --- Conversion summary (denormalised for fast dashboard reads) ---
    total_clicks: int = Field(default=0, ge=0)
    total_conversions: int = Field(default=0, ge=0)
    estimated_roi: Optional[float] = Field(
        None,
        description="(Revenue from conversions - fee) / fee * 100. Calculated by ML service.",
    )

    status: CollaborationStatus = Field(default=CollaborationStatus.INVITED)
    invited_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# CampaignCreatorBrief
# ---------------------------------------------------------------------------

class CampaignCreatorBrief(BaseModel):
    """
    The creative brief that an SME sends to a creator for a collaboration.
    Stores deliverables, dos/don'ts, and brand guidelines.

    Backend maps this to the `campaign_creator_briefs` table.

    Indexes:
        - collaboration_id (unique FK — one brief per collaboration)
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    collaboration_id: UUID = Field(..., description="FK → campaign_collaborations.id")

    deliverables: str = Field(
        ..., max_length=2000,
        description="What the creator must produce, e.g. '1 YouTube video, 3 IG stories'.",
    )
    dos: List[str] = Field(
        default_factory=list,
        description="Things the creator MUST include or do.",
    )
    donts: List[str] = Field(
        default_factory=list,
        description="Things the creator must NOT do or say.",
    )
    brand_keywords: List[str] = Field(
        default_factory=list,
        description="Mandatory talking points or brand mentions.",
    )
    hashtags_required: List[str] = Field(
        default_factory=list,
        description="Mandatory hashtags.",
    )
    reference_links: List[str] = Field(
        default_factory=list,
        description="Links to inspiration, product pages, or brand guidelines PDF.",
    )
    submission_deadline: Optional[date] = Field(None)
    revision_limit: int = Field(default=2, ge=0, description="Max revisions SME can request.")
    additional_notes: Optional[str] = Field(None, max_length=1000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# ConversionEvent (granular — one row per individual conversion action)
# ---------------------------------------------------------------------------

class ConversionEvent(BaseModel):
    """
    A single conversion event triggered by a user clicking a creator's
    tracking link. Received via webhook from the SME's website or our
    tracking pixel.

    Backend maps this to the `conversion_events` table.

    Indexes:
        - collaboration_id + event_type
        - occurred_at DESC
        - tracking_code (for ingest lookup)

    Partitioning:
        Partition by range on occurred_at (monthly) for performance.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    collaboration_id: UUID = Field(..., description="FK → campaign_collaborations.id")

    event_type: ConversionEventType = Field(...)
    occurred_at: datetime = Field(..., description="When the event actually happened.")
    received_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When our system received the webhook.",
    )

    # --- Attribution ---
    tracking_code: str = Field(
        ..., description="Short code used to resolve collaboration_id on ingest."
    )

    # --- Optional enrichment from webhook payload ---
    revenue_ngn: Optional[float] = Field(
        None, ge=0, description="Revenue generated by this specific event (for PURCHASE)."
    )
    session_id: Optional[str] = Field(None, description="Browser session for deduplication.")
    ip_country: Optional[str] = Field(None, max_length=2, description="ISO 3166-1 country code.")
    device_type: Optional[str] = Field(None, description="mobile | desktop | tablet")
    custom_data: Optional[Dict[str, str]] = Field(
        None, description="Any extra key-value pairs from the webhook payload."
    )