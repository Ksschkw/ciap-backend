from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    project_name: str = "CIAP API"
    api_v1_prefix: str = "/api/v1"
    youtube_api_key: str = Field(default="")
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    oauth_redirect_uri: str = Field(default="http://localhost:8000/api/v1/oauth/youtube/callback")
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/ciap")
    redis_url: str = Field(default="redis://localhost:6379/0")
    secret_key: str = Field(default="dev-secret-key-change-me-dev-secret-key")
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_recycle_seconds: int = 1800
    database_pool_timeout_seconds: int = 30

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key == "dev-secret-key-change-me-dev-secret-key":
                raise ValueError("secret_key must be set to a production value")
            if "localhost" in self.database_url:
                raise ValueError("database_url must point to a production database")
            if "localhost" in self.redis_url:
                raise ValueError("redis_url must point to a production Redis instance")

        return self


settings = Settings()
