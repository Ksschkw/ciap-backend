from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.schemas import AuthLoginRequest, AuthRegisterRequest, AuthRefreshRequest
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password, decode_token
from app.config import settings
from DATA.models.users import User
from DATA.data_connections.repositories.user_repo import SQLUserRepository

@dataclass(slots=True)
class AuthService:
    session: Session

    def register(self, payload: AuthRegisterRequest) -> dict[str, Any]:
        repository = SQLUserRepository(self.session)
        existing_user = repository.get_by_email(payload.email)
        if existing_user is not None:
            raise ConflictError("A user with this email already exists")

        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            full_name=payload.full_name,
            language_preference=payload.language_preference,
        )
        repository.create(user)

        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
                "language_preference": user.language_preference,
                "access_token": create_access_token(str(user.id), extra_claims={"email": user.email, "role": user.role}),
                "refresh_token": create_refresh_token(str(user.id), extra_claims={"email": user.email, "role": user.role}),
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
            },
        }

    def login(self, payload: AuthLoginRequest) -> dict[str, Any]:
        repository = SQLUserRepository(self.session)
        user = repository.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
                "language_preference": user.language_preference,
                "access_token": create_access_token(str(user.id), extra_claims={"email": user.email, "role": user.role}),
                "refresh_token": create_refresh_token(str(user.id), extra_claims={"email": user.email, "role": user.role}),
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
            },
        }

    def refresh(self, payload: AuthRefreshRequest) -> dict[str, Any]:
        repository = SQLUserRepository(self.session)
        try:
            token_payload = decode_token(payload.refresh_token)
            if token_payload.get("token_type") != "refresh":
                raise UnauthorizedError("Invalid token type")
            user_id = UUID(str(token_payload.get("sub")))
        except (TypeError, ValueError, KeyError):
            raise UnauthorizedError("Invalid or expired refresh token")

        user = repository.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")

        return {
            "success": True,
            "message": "Token refreshed successfully",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "access_token": create_access_token(str(user.id), extra_claims={"email": user.email, "role": user.role}),
                "refresh_token": create_refresh_token(str(user.id), extra_claims={"email": user.email, "role": user.role}),
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
            },
        }

    def get_me(self, user_id: str) -> dict[str, Any]:
        from DATA.data_connections.repositories.concrete import (
            SQLCreatorProfileRepository,
            SQLPlatformConnectionRepository,
            SQLInfluenceScoreRepository,
        )
        from uuid import UUID

        uid = UUID(str(user_id))
        user_repo = SQLUserRepository(self.session)
        user = user_repo.get_by_id(uid)
        if not user:
            raise UnauthorizedError("User not found")

        creator_repo = SQLCreatorProfileRepository(self.session)
        conn_repo    = SQLPlatformConnectionRepository(self.session)

        creator_profile = None
        if user.role == "CREATOR":
            cp = creator_repo.get_by_user_id(uid)
            if cp:
                score_repo   = SQLInfluenceScoreRepository(self.session)
                latest_score = score_repo.latest_for_creator(cp.id)

                followers    = getattr(cp, "total_followers", None) or getattr(cp, "followers", None) or 0
                social       = getattr(cp, "social_handles", None) or getattr(cp, "social_links", None) or {}
                city         = getattr(cp, "location_city", None)
                country      = getattr(cp, "location_country", None)
                location     = f"{city}, {country}" if city and country else city or country

                creator_profile = {
                    # ── IDs (frontend MUST use creator_profile_id for content/analytics calls) ──
                    "creator_profile_id": str(cp.id),
                    "user_id":            str(uid),
                    # ── Profile fields ──
                    "category":           cp.category,
                    "bio":                cp.bio,
                    "location":           location,
                    "total_followers":    followers,
                    "is_public":          cp.is_public,
                    "social_links":       social,
                    # ── Score snapshot ──
                    "influence_score":    latest_score.score if latest_score else (cp.influence_score or 0),
                    "score_tier":         self._tier(latest_score.score if latest_score else (cp.influence_score or 0)),
                }

        platforms = conn_repo.get_active_connections_for_user(uid)

        return {
            "success": True,
            "message": "User profile retrieved successfully",
            "data": {
                "user": {
                    "id":                  str(user.id),
                    "email":               user.email,
                    "role":                user.role,
                    "full_name":           user.full_name,
                    "avatar_url":          user.avatar_url,
                    "language_preference": user.language_preference,
                    "status":              user.status,
                },
                "creator_profile": creator_profile,
                "connected_platforms": [
                    {
                        "platform_name":    p.platform_name,
                        "platform_user_id": p.platform_user_id,
                        "username":         p.platform_username,
                        "is_active":        p.is_active,
                        "last_synced_at":   p.last_synced_at.isoformat() if p.last_synced_at else None,
                        "needs_sync":       p.last_synced_at is None,
                    }
                    for p in platforms
                ],
            },
        }

    @staticmethod
    def _tier(score: float) -> str:
        if score >= 80: return "Mega"
        if score >= 60: return "Macro"
        if score >= 40: return "Mid-Tier"
        if score >= 20: return "Micro"
        return "Nano"

