from .base import Base
from .users import User, CreatorProfile, SMEProfile, PlatformConnection, AuditLog, Notification
from .content import ContentItem, ContentMetricSnapshot, AudienceSnapshot
from .campaigns import Campaign, CampaignCollaboration, CampaignCreatorBrief, ConversionEvent
from .scoring import InfluenceScore
from .messages import Message

# This allows Alembic to import `Base` and see all defined tables
__all__ = [
    "Base",
    "User", "CreatorProfile", "SMEProfile", "PlatformConnection", "AuditLog", "Notification",
    "ContentItem", "ContentMetricSnapshot", "AudienceSnapshot",
    "Campaign", "CampaignCollaboration", "CampaignCreatorBrief", "ConversionEvent",
    "InfluenceScore", "Message"
]