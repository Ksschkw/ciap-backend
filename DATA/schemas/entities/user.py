"""
User-related entity models.

Maps 1-to-1 with PostgreSQL tables defined in schema_erd.mmd.
Backend team uses these as the basis for SQLAlchemy ORM models
(with model_config = ConfigDict(from_attributes=True)).

Tables covered:
    User                - Core account for every person in the system
    CreatorProfile      - Extended profile only for CREATOR role users
    SMEProfile          - Extended profile only for SME/AGENCY role users
    PlatformConnection  - OAuth token storage per platform per user
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    """Roles that determine access level and profile type."""
    CREATOR = "CREATOR"
    SME = "SME"
    AGENCY = "AGENCY"
    ADMIN = "ADMIN"


class LanguagePreference(str, enum.Enum):
    """Supported UI languages — critical for Nigerian/African localisation."""
    ENGLISH = "en"
    HAUSA = "ha"
    YORUBA = "yo"
    IGBO = "ig"
    PIDGIN = "pcm"


class Platform(str, enum.Enum):
    """All social platforms we integrate with. Used in multiple models."""
    YOUTUBE = "YOUTUBE"
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"
    TWITTER = "TWITTER"
    FACEBOOK = "FACEBOOK"
    SPOTIFY = "SPOTIFY"
    AUDIOMACK = "AUDIOMACK"
    SNAPCHAT = "SNAPCHAT"


class CreatorCategory(str, enum.Enum):
    """Content niche/category used for discovery and ML segmentation."""
    MUSIC = "Music"
    COMEDY = "Comedy"
    TECH = "Tech"
    FASHION = "Fashion"
    BEAUTY = "Beauty"
    FOOD = "Food"
    SPORTS = "Sports"
    LIFESTYLE = "Lifestyle"
    EDUCATION = "Education"
    POLITICS = "Politics"
    ENTERTAINMENT = "Entertainment"
    GAMING = "Gaming"
    TRAVEL = "Travel"
    BUSINESS = "Business"
    HEALTH = "Health"
    OTHER = "Other"


class AccountStatus(str, enum.Enum):
    """Lifecycle status of any user account."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    DEACTIVATED = "DEACTIVATED"


class SubscriptionPlan(str, enum.Enum):
    """Monetisation tiers. FREE is default for all new users."""
    FREE = "FREE"
    CREATOR_PRO = "CREATOR_PRO"
    SME_STARTER = "SME_STARTER"
    SME_GROWTH = "SME_GROWTH"
    AGENCY = "AGENCY"
    ENTERPRISE = "ENTERPRISE"


# ---------------------------------------------------------------------------
# User (core account — every person in the system)
# ---------------------------------------------------------------------------

class User(BaseModel):
    """
    Core user account table. All roles share this.
    Backend maps this to the `users` PostgreSQL table.

    Indexes (hint for Backend):
        - email (unique)
        - role
        - status
        - created_at DESC
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Primary key.")
    email: EmailStr = Field(..., description="Unique login email.")
    hashed_password: Optional[str] = Field(
        None,
        description="Bcrypt hash. NULL for OAuth-only signups.",
    )
    role: UserRole = Field(..., description="Determines which profile table is populated.")
    full_name: str = Field(..., min_length=2, max_length=120, description="Display name.")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL (CDN).")
    language_preference: LanguagePreference = Field(
        default=LanguagePreference.ENGLISH,
        description="User's preferred UI language.",
    )
    status: AccountStatus = Field(
        default=AccountStatus.PENDING_VERIFICATION,
        description="Account lifecycle state.",
    )
    subscription_plan: SubscriptionPlan = Field(
        default=SubscriptionPlan.FREE,
        description="Current monetisation tier.",
    )
    is_email_verified: bool = Field(default=False)
    last_login_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


# ---------------------------------------------------------------------------
# CreatorProfile
# ---------------------------------------------------------------------------

class CreatorProfile(BaseModel):
    """
    Extended profile for CREATOR role users. 1-to-1 with User.
    Backend maps this to the `creator_profiles` table.

    Indexes:
        - user_id (unique FK)
        - influence_score DESC (for SME sorting)
        - category
        - is_public
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="FK → users.id")
    category: CreatorCategory = Field(..., description="Primary content niche.")
    secondary_categories: List[CreatorCategory] = Field(
        default_factory=list,
        description="Up to 2 additional niches stored as JSON array.",
    )
    bio: Optional[str] = Field(None, max_length=500)
    location_country: Optional[str] = Field(None, max_length=2, description="ISO 3166-1 alpha-2.")
    location_city: Optional[str] = Field(None, max_length=80)
    social_handles: Dict[str, str] = Field(
        default_factory=dict,
        description="Display handles: {'youtube': '@Handle', 'instagram': '@handle'}",
    )
    influence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="ML-calculated weekly score 0–100.",
    )
    total_followers: Optional[int] = Field(
        None, ge=0, description="Aggregated follower count across all connected platforms."
    )
    avg_engagement_rate: Optional[float] = Field(
        None, ge=0.0, description="Aggregated engagement rate (%). Recalculated weekly."
    )
    is_public: bool = Field(
        default=True,
        description="Whether SMEs can discover this creator.",
    )
    is_verified: bool = Field(
        default=False,
        description="Platform-verified badge (admin-granted).",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# SMEProfile
# ---------------------------------------------------------------------------

class SMEProfile(BaseModel):
    """
    Extended profile for SME and AGENCY role users. 1-to-1 with User.
    Backend maps this to the `sme_profiles` table.

    Indexes:
        - user_id (unique FK)
        - industry
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="FK → users.id")
    company_name: str = Field(..., min_length=2, max_length=200)
    industry: str = Field(..., max_length=100, description="e.g., FMCG, Fintech, Fashion.")
    website_url: Optional[str] = Field(None, description="Company website.")
    logo_url: Optional[str] = Field(None, description="Company logo (CDN).")
    description: Optional[str] = Field(None, max_length=500)
    # Billing is a reference to payment gateway records — NOT stored raw.
    payment_gateway_customer_id: Optional[str] = Field(
        None,
        description="Paystack/Flutterwave customer ID. Never store card details here.",
    )
    monthly_budget_ngn: Optional[float] = Field(
        None, ge=0, description="Self-declared monthly influencer marketing budget in NGN."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# PlatformConnection (OAuth token storage)
# ---------------------------------------------------------------------------

class PlatformConnection(BaseModel):
    """
    Stores OAuth 2.0 tokens for a user's connected social platform account.
    One user can connect multiple platforms (one row per platform).

    SECURITY NOTE (for Backend):
        access_token and refresh_token MUST be encrypted at rest using
        Fernet or AWS KMS before writing to the database. Never log them.

    Indexes:
        - user_id + platform_name (unique composite — one per platform)
        - is_active
        - token_expires_at (for scheduled refresh jobs)
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="FK → users.id")
    platform_name: Platform = Field(..., description="Which platform this token is for.")
    access_token: str = Field(..., description="ENCRYPTED. OAuth access token.")
    refresh_token: Optional[str] = Field(None, description="ENCRYPTED. OAuth refresh token.")
    token_expires_at: Optional[datetime] = Field(
        None, description="When the access_token expires. NULL = non-expiring."
    )
    # The user's native ID on the external platform (e.g., YouTube channel ID).
    platform_user_id: str = Field(..., description="Creator's ID on the external platform.")
    platform_username: Optional[str] = Field(
        None, description="Display username/handle on the platform."
    )
    scopes_granted: List[str] = Field(
        default_factory=list,
        description="OAuth scopes the user approved, e.g. ['read:metrics', 'read:audience']",
    )
    is_active: bool = Field(
        default=True,
        description="Set False when token is revoked or refresh fails.",
    )
    last_synced_at: Optional[datetime] = Field(
        None, description="Timestamp of the most recent successful data pull."
    )
    sync_error_message: Optional[str] = Field(
        None, description="Last error from ingestion job, if any."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)