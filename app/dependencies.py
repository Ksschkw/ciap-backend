from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from DATA.data_connections.repositories.user_repo import SQLUserRepository
from DATA.core.database import get_db
from app.services import (
    AdminService,
    AnalyticsService,
    AuthService,
    CampaignService,
    CreatorService,
    DiscoverService,
    ForecastService,
    OAuthService,
    PlatformService,
    ReportService,
    ScoreService,
    SmeService,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    return settings


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> dict[str, str]:
    token = request.cookies.get("access_token")
    if not token and credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    if not token:
        raise UnauthorizedError("Missing or invalid authorization header or cookie")

    try:
        payload = decode_token(token)
        if payload.get("token_type") != "access":
            raise UnauthorizedError("Invalid token type")
        user_id = UUID(str(payload.get("sub")))
    except (JWTError, TypeError, ValueError):
        raise UnauthorizedError("Invalid or expired token")

    user = SQLUserRepository(session).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User not found")

    return {"id": str(user.id), "email": str(user.email), "role": str(user.role)}


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> dict[str, str] | None:
    token = request.cookies.get("access_token")
    if not token and credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    if not token:
        return None

    try:
        payload = decode_token(token)
        if payload.get("token_type") != "access":
            return None
        user_id = UUID(str(payload.get("sub")))
    except (JWTError, TypeError, ValueError):
        return None

    user = SQLUserRepository(session).get_by_id(user_id)
    if user is None:
        return None

    return {"id": str(user.id), "email": str(user.email), "role": str(user.role)}


def get_auth_service(session: Session = Depends(get_db)) -> AuthService:
    return AuthService(session=session)


def get_creator_service(session: Session = Depends(get_db)) -> CreatorService:
    return CreatorService(session=session)


def get_platform_service(session: Session = Depends(get_db)) -> PlatformService:
    return PlatformService(session=session)


def get_analytics_service(session: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(session=session)


def get_score_service(session: Session = Depends(get_db)) -> ScoreService:
    return ScoreService(session=session)


def get_sme_service(session: Session = Depends(get_db)) -> SmeService:
    return SmeService(session=session)


def get_discover_service(session: Session = Depends(get_db)) -> DiscoverService:
    return DiscoverService(session=session)


def get_campaign_service(session: Session = Depends(get_db)) -> CampaignService:
    return CampaignService(session=session)


def get_forecast_service(session: Session = Depends(get_db)) -> ForecastService:
    return ForecastService(session=session)


def get_report_service(session: Session = Depends(get_db)) -> ReportService:
    return ReportService(session=session)


def get_admin_service(session: Session = Depends(get_db)) -> AdminService:
    return AdminService(session=session)


def get_oauth_service(session: Session = Depends(get_db)) -> OAuthService:
    return OAuthService(session=session)
