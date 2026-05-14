from __future__ import annotations

import httpx
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from DATA.data_connections.repositories.concrete import (
    SQLUserRepository,
    SQLCreatorProfileRepository,
    SQLPlatformConnectionRepository,
)
from DATA.models.users import User, CreatorProfile, PlatformConnection
from app.core.security import create_access_token, create_refresh_token

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@dataclass(slots=True)
class OAuthService:
    session: Session

    def connect(self, platform: str, user_id: str | None = None) -> dict[str, Any]:
        if platform.lower() != "youtube":
            raise HTTPException(status_code=400, detail="Only youtube is supported")

        if not settings.google_client_id:
            raise HTTPException(status_code=500, detail="Google Client ID not configured")

        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.oauth_redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email",
            "access_type": "offline",
            "prompt": "consent",
        }
        
        if user_id:
            params["state"] = user_id
            
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return {"success": True, "message": f"Connect flow started for {platform}", "data": {"auth_url": url}}

    def callback(self, platform: str, code: str, state: str | None = None) -> dict[str, Any]:
        if platform.lower() != "youtube":
            raise HTTPException(status_code=400, detail="Only youtube is supported")

        if not code:
            raise HTTPException(status_code=400, detail="Authorization code missing")

        # 1. Exchange code for tokens
        token_data = {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.oauth_redirect_uri,
        }

        with httpx.Client() as client:
            token_res = client.post(GOOGLE_TOKEN_URL, data=token_data)
            if token_res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to exchange token: {token_res.text}")
            
            tokens = token_res.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            # 2. Get user info
            headers = {"Authorization": f"Bearer {access_token}"}
            user_res = client.get(GOOGLE_USERINFO_URL, headers=headers)
            if user_res.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user info")
            
            user_info = user_res.json()

        email = user_info.get("email")
        full_name = user_info.get("name")
        avatar_url = user_info.get("picture")
        
        if not email:
            raise HTTPException(status_code=400, detail="No email associated with Google account")

        # Fetch YouTube Channel ID (mine=true)
        yt_channel_id = None
        with httpx.Client() as client:
            yt_res = client.get("https://www.googleapis.com/youtube/v3/channels?part=id&mine=true", headers={"Authorization": f"Bearer {access_token}"})
            if yt_res.status_code == 200 and yt_res.json().get("items"):
                yt_channel_id = yt_res.json()["items"][0]["id"]
        
        platform_user_id = yt_channel_id or user_info.get("id")

        # 3. DB Logic
        user_repo = SQLUserRepository(self.session)
        profile_repo = SQLCreatorProfileRepository(self.session)
        conn_repo = SQLPlatformConnectionRepository(self.session)

        user = None
        
        # If state is provided, the user was already logged in when they initiated the connection
        if state:
            try:
                from uuid import UUID
                user = user_repo.get_by_id(UUID(state))
            except ValueError:
                pass
                
        if not user:
            user = user_repo.get_by_email(email)
            
        if not user:
            # Create user
            user = User(
                email=email,
                role="CREATOR",
                full_name=full_name,
                avatar_url=avatar_url,
                is_email_verified=True,
                status="ACTIVE"
            )
            user_repo.create(user)
            
            # Create CreatorProfile
            profile = CreatorProfile(
                user_id=user.id,
                category="General", # Default category
                is_public=True
            )
            profile_repo.create(profile)
        
        # Upsert PlatformConnection and handle merging dummy accounts
        conn = conn_repo.get_by_user_and_platform(user.id, "YOUTUBE")
        
        # Check if the channel was already ingested by a dummy account
        if not conn and yt_channel_id:
            existing_conn = self.session.query(PlatformConnection).filter(PlatformConnection.platform_user_id == yt_channel_id).first()
            if existing_conn and existing_conn.user_id != user.id:
                dummy_user = user_repo.get_by_id(existing_conn.user_id)
                if dummy_user and dummy_user.email.endswith("@youtube-ingested.ciap"):
                    # Merge dummy account into current user
                    dummy_profile = profile_repo.get_by_user_id(dummy_user.id)
                    if dummy_profile:
                        dummy_profile.user_id = user.id
                        self.session.flush()
                    
                    existing_conn.user_id = user.id
                    existing_conn.access_token = access_token
                    existing_conn.refresh_token = refresh_token or existing_conn.refresh_token
                    self.session.flush()
                    
                    dummy_user.is_merged = True
                    dummy_user.merged_into_id = user.id
                    dummy_user.status = "MERGED"
                    self.session.flush()
                    
                    conn = existing_conn

        if conn:
            conn_repo.update_tokens(
                connection_id=conn.id,
                new_access_token=access_token,
                new_refresh_token=refresh_token or conn.refresh_token,
                new_expires_at=None
            )
        else:
            conn = PlatformConnection(
                user_id=user.id,
                platform_name="YOUTUBE",
                platform_user_id=platform_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                is_active=True
            )
            conn_repo.create(conn)

        # 4. Generate JWT
        jwt_access_token = create_access_token(str(user.id), extra_claims={"email": user.email, "role": user.role})
        jwt_refresh_token = create_refresh_token(str(user.id), extra_claims={"email": user.email, "role": user.role})

        return {
            "success": True,
            "message": f"Successfully connected {platform} and logged in",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "access_token": jwt_access_token,
                "refresh_token": jwt_refresh_token,
                "token_type": "bearer"
            }
        }
