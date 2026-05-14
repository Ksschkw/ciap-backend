"""
CIAP DATA Package — top-level entry point.
==========================================

This is the encapsulated Data + Database layer for the
Creative Influence & Analytics Platform (CIAP) MVP.

It is the single source of truth for:
    - PostgreSQL ORM models   (DATA.models)
    - Pydantic schemas        (DATA.schemas)
    - Database session        (DATA.core)
    - Repository interfaces   (DATA.data_connections.repositories)
    - External API clients    (DATA.data_connections.external_apis)

The backend package (backend/) imports exclusively from here.
Frontend devs reference DATA.schemas.responses for API shape contracts.

Quick reference:
    from DATA.core import get_db, engine
    from DATA.models import User, ContentItem, Campaign
    from DATA.schemas.entities import UserRole, Platform, CampaignStatus
    from DATA.schemas.requests import LoginRequest, CreateCampaignRequest
    from DATA.schemas.responses import CreatorDashboardResponse
    from DATA.data_connections.repositories import (
        IUserRepository, IContentRepository, ICampaignRepository
    )
    from DATA.data_connections.external_apis import BaseAPIClient, MockAPIClient
"""