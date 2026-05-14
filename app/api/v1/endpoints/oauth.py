from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_oauth_service, get_current_user_optional
from app.services.oauth_service import OAuthService
from app.api.v1.endpoints.auth import _set_auth_cookies

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/{platform}/connect", summary="Initiate OAuth Connection", response_description="OAuth Authorization URL")
def connect(
    platform: str, 
    oauth_service: OAuthService = Depends(get_oauth_service),
    current_user: dict[str, str] | None = Depends(get_current_user_optional)
) -> dict[str, object]:
    """
    Get the OAuth authorization URL for a specific platform (e.g., 'youtube').
    
    **FRONTEND USAGE NOTE**: 
    The frontend does *not* necessarily need to use this endpoint to initiate the OAuth flow.
    If you already have the Google Client ID configured on the frontend, you can initiate 
    the Google/YouTube OAuth flow directly from the client application. 
    
    Once the frontend completes the flow and receives the `code`, it can simply pass that 
    code directly to the `/{platform}/callback` endpoint below to complete the connection.
    """
    user_id = str(current_user["id"]) if current_user else None
    return oauth_service.connect(platform, user_id=user_id)


@router.get("/{platform}/callback", summary="Handle OAuth Callback", response_description="Tokens and user info")
def callback(
    platform: str, 
    code: str, 
    response: Response,
    state: str | None = None,
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> dict[str, object]:
    """
    Handle the OAuth callback after successful authorization.
    
    This endpoint exchanges the authorization `code` for access and refresh tokens, 
    and links the platform account (e.g., YouTube) to the authenticated user.
    
    **FRONTEND USAGE NOTE**:
    If the frontend handles the OAuth popup/redirect directly using the Google Client ID,
    it should take the `code` returned by Google and send it to this endpoint (e.g., via 
    query parameters `?code=...&platform=youtube`) to finalize the connection.
    """
    result = oauth_service.callback(platform, code, state=state)
    _set_auth_cookies(response, result.get("data", {}))
    return result
