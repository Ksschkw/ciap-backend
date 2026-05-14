"""
Data connections layer — single import point.

Usage:
    from DATA.data_connections.repositories import IUserRepository, ICampaignRepository, ...
    from DATA.data_connections.external_apis import BaseAPIClient
"""

from DATA.data_connections.repositories import (
    IAudienceSnapshotRepository,
    IAuditLogRepository,
    IBriefRepository,
    ICampaignRepository,
    ICollaborationRepository,
    IContentMetricRepository,
    IContentRepository,
    IConversionEventRepository,
    ICreatorProfileRepository,
    IInfluenceScoreRepository,
    INotificationRepository,
    IPlatformConnectionRepository,
    IRepository,
    ISMEProfileRepository,
    IUserRepository,
)
from DATA.data_connections.external_apis import BaseAPIClient

__all__ = [
    "IRepository",
    "IUserRepository", "ICreatorProfileRepository",
    "ISMEProfileRepository", "IPlatformConnectionRepository",
    "IContentRepository", "IContentMetricRepository", "IAudienceSnapshotRepository",
    "ICampaignRepository", "ICollaborationRepository",
    "IBriefRepository", "IConversionEventRepository",
    "IInfluenceScoreRepository",
    "INotificationRepository", "IAuditLogRepository",
    "BaseAPIClient",
]