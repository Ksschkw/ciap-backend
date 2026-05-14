from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AuthRole = Literal["CREATOR", "SME", "ADMIN"]
CampaignStatus = Literal["DRAFT", "ACTIVE", "PAUSED", "COMPLETED"]
ExportFormat = Literal["pdf", "csv", "xlsx"]


from pydantic import BaseModel, Field, ConfigDict

class AuthRegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "role": "CREATOR",
                "full_name": "John Doe",
                "language_preference": "en"
            }
        }
    )
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=128)
    role: AuthRole = "CREATOR"
    full_name: str | None = Field(default=None, max_length=255)
    language_preference: str | None = Field(default=None, max_length=16)


class AuthLoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=128)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    goal: str | None = Field(default=None, max_length=100)
    budget: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None


class CampaignUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    goal: str | None = Field(default=None, max_length=100)
    budget: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    status: CampaignStatus | None = None


class ForecastRequest(BaseModel):
    creator_id: UUID
    budget: float = Field(gt=0)
    duration_days: int = Field(gt=0)
    goal: str = Field(default="awareness", min_length=1, max_length=120)


class PlatformSyncRequest(BaseModel):
    platforms: list[str] | None = None