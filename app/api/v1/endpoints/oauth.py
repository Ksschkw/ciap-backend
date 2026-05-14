from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_oauth_service, get_current_user_optional
from app.services.oauth_service import OAuthService
from app.api.v1.endpoints.auth import _set_auth_cookies

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/{platform}/connect")
def connect(
    platform: str, 
    oauth_service: OAuthService = Depends(get_oauth_service),
    current_user: dict[str, str] | None = Depends(get_current_user_optional)
) -> dict[str, object]:
    user_id = str(current_user["id"]) if current_user else None
    return oauth_service.connect(platform, user_id=user_id)


@router.get("/{platform}/callback")
def callback(
    platform: str, 
    code: str, 
    response: Response,
    state: str | None = None,
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> dict[str, object]:
    result = oauth_service.callback(platform, code, state=state)
    _set_auth_cookies(response, result.get("data", {}))
    return result
