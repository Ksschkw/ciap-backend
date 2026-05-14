"""
Repository interfaces — single import point.

Usage:
    from DATA.data_connections.repositories import (
        IUserRepository,
        ICreatorProfileRepository,
        IContentRepository,
        ICampaignRepository,
        ...
    )
"""

from DATA.data_connections.repositories.base import IRepository
from DATA.data_connections.repositories.user_repo import (
    ICreatorProfileRepository,
    IPlatformConnectionRepository,
    ISMEProfileRepository,
    IUserRepository,
    SQLUserRepository,
)
from DATA.data_connections.repositories.content_repo import (
    IAudienceSnapshotRepository,
    IContentMetricRepository,
    IContentRepository,
)
from DATA.data_connections.repositories.campaign_repo import (
    IAuditLogRepository,
    IBriefRepository,
    ICampaignRepository,
    ICollaborationRepository,
    IConversionEventRepository,
    IInfluenceScoreRepository,
    INotificationRepository,
)

from DATA.data_connections.repositories.concrete import (
    SQLCreatorProfileRepository,
    SQLSMEProfileRepository,
    SQLPlatformConnectionRepository,
    SQLCampaignRepository,
    SQLContentRepository,
    SQLInfluenceScoreRepository,
    SQLAudienceSnapshotRepository,
    SQLContentMetricRepository,
)

__all__ = [
    "IRepository",
    # User domain
    "IUserRepository",
    "ICreatorProfileRepository",
    "ISMEProfileRepository",
    "IPlatformConnectionRepository",
    # Content domain
    "IContentRepository",
    "IContentMetricRepository",
    "IAudienceSnapshotRepository",
    # Campaign domain
    "ICampaignRepository",
    "ICollaborationRepository",
    "IBriefRepository",
    "IConversionEventRepository",
    # ML / Scoring
    "IInfluenceScoreRepository",
    # Notifications & Audit
    "INotificationRepository",
    "IAuditLogRepository",
    "SQLCreatorProfileRepository",
    "SQLSMEProfileRepository",
    "SQLPlatformConnectionRepository",
    "SQLCampaignRepository",
    "SQLContentRepository",
    "SQLInfluenceScoreRepository",
    "SQLAudienceSnapshotRepository",
    "SQLUserRepository",
    "SQLContentMetricRepository",
]