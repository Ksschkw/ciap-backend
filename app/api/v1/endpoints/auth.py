from __future__ import annotations

from fastapi import APIRouter, Depends, status, Response

from app.api.v1.schemas import AuthLoginRequest, AuthRefreshRequest, AuthRegisterRequest
from app.dependencies import get_auth_service, get_current_user
from app.services.auth_service import AuthService
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

def _set_auth_cookies(response: Response, data: dict):
    if "access_token" in data:
        response.set_cookie(
            key="access_token",
            value=data["access_token"],
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60,
        )
    if "refresh_token" in data:
        response.set_cookie(
            key="refresh_token",
            value=data["refresh_token"],
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        )

@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register New User", response_description="Tokens and user info")
def register(payload: AuthRegisterRequest, response: Response, auth_service: AuthService = Depends(get_auth_service)) -> dict[str, object]:
    """
    Register a new user account (SME or standard user) using an email and password.
    
    Automatically sets secure HTTP-only cookies (`access_token`, `refresh_token`) upon 
    success and also returns them in the JSON body.
    """
    result = auth_service.register(payload)
    _set_auth_cookies(response, result["data"])
    return result


@router.post("/login", summary="Login User", response_description="Tokens and user info")
def login(payload: AuthLoginRequest, response: Response, auth_service: AuthService = Depends(get_auth_service)) -> dict[str, object]:
    """
    Authenticate a user with email and password.
    
    Automatically sets secure HTTP-only cookies (`access_token`, `refresh_token`) upon 
    success and also returns them in the JSON body.
    """
    result = auth_service.login(payload)
    _set_auth_cookies(response, result["data"])
    return result


@router.post("/refresh", summary="Refresh Access Token", response_description="New tokens")
def refresh(payload: AuthRefreshRequest, response: Response, auth_service: AuthService = Depends(get_auth_service)) -> dict[str, object]:
    """
    Generate a new access token using a valid refresh token.
    
    Updates the secure HTTP-only cookies with the newly issued tokens.
    """
    result = auth_service.refresh(payload)
    _set_auth_cookies(response, result["data"])
    return result


@router.get("/me", summary="Get Current Profile", response_description="Complete profile data for the logged-in user")
def get_me(current_user: dict[str, str] = Depends(get_current_user), auth_service: AuthService = Depends(get_auth_service)) -> dict[str, object]:
    """
    Retrieve the profile information for the currently authenticated user.
    
    Depending on their role (SME or CREATOR), this returns their specific profile
    details, including connected social platforms.
    """
    return auth_service.get_me(current_user["id"])
