"""
DATA.schemas.entities — single import point for all Pydantic entity schemas.

These are the Pydantic validation/serialization models.
They are NOT the database tables (those live in DATA.models).
They are used:
  - To validate incoming API request bodies
  - To serialize outgoing API responses
  - As the canonical "shape" contract between DATA, backend, and frontend

Usage:
    from DATA.schemas.entities import (
        User, CreatorProfile, SMEProfile, PlatformConnection,
        ContentItem, ContentMetricSnapshot, AudienceSnapshot,
        Campaign, CampaignCollaboration, CampaignCreatorBrief, ConversionEvent,
        InfluenceScore, ScoreBreakdown,
    )
"""

# User domain
from DATA.schemas.entities.user import (
    User,
    UserRole,
    AccountStatus,
    SubscriptionPlan,
    LanguagePreference,
    Platform,
    CreatorCategory,
    CreatorProfile,
    SMEProfile,
    PlatformConnection,
)

# Content domain
from DATA.schemas.entities.content import (
    ContentItem,
    ContentStatus,
    MediaType,
    ContentMetricSnapshot,
    AudienceSnapshot,
)

# Campaign domain
from DATA.schemas.entities.campaign import (
    Campaign,
    CampaignStatus,
    CampaignObjective,
    CampaignCollaboration,
    CollaborationStatus,
    CampaignCreatorBrief,
    ConversionEvent,
    ConversionEventType,
)

# ML / Scoring domain
from DATA.schemas.entities.scoring import (
    InfluenceScore,
    ScoreBreakdown,
)

__all__ = [
    # User domain
    "User", "UserRole", "AccountStatus", "SubscriptionPlan",
    "LanguagePreference", "Platform", "CreatorCategory",
    "CreatorProfile", "SMEProfile", "PlatformConnection",
    # Content domain
    "ContentItem", "ContentStatus", "MediaType",
    "ContentMetricSnapshot", "AudienceSnapshot",
    # Campaign domain
    "Campaign", "CampaignStatus", "CampaignObjective",
    "CampaignCollaboration", "CollaborationStatus",
    "CampaignCreatorBrief", "ConversionEvent", "ConversionEventType",
    # ML / Scoring
    "InfluenceScore", "ScoreBreakdown",
]