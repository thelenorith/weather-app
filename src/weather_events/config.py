"""Application configuration.

Configuration is loaded from environment variables using pydantic-settings.
All sensitive values (secrets, API keys) should be provided via environment
variables, not config files.

## Required Environment Variables

- SECRET_KEY: Application secret for session signing and encryption
- DATABASE_URL: PostgreSQL connection string

## Optional Environment Variables

- GOOGLE_CLIENT_ID: Google OAuth client ID
- GOOGLE_CLIENT_SECRET: Google OAuth client secret
- ENCRYPTION_SALT: Salt for token encryption (default: derived from SECRET_KEY)
- DEBUG: Enable debug mode (default: false)

## Example .env file

```
SECRET_KEY=your-secret-key-at-least-32-characters
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/weather_events
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```
"""

from __future__ import annotations

import hashlib
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Weather Event Recommendations"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Security
    secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key for signing and encryption (min 32 chars)",
    )
    encryption_salt: str = Field(
        default="",
        description="Salt for token encryption (auto-generated if not provided)",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string",
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=50)
    database_echo: bool = False  # Log SQL queries

    # Google OAuth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Google Calendar API
    google_calendar_scopes: list[str] = Field(
        default=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        description="Google Calendar API scopes",
    )

    # Weather providers
    default_weather_provider: str = "metno"
    metno_user_agent: str = Field(
        default="weather-events/0.1.0 github.com/weather-events",
        description="User-Agent for MET Norway API (required)",
    )
    pirateweather_api_key: str | None = None

    # Session
    session_cookie_name: str = "weather_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7  # 7 days

    # Calendar sync
    default_poll_interval_minutes: int = Field(default=15, ge=5, le=1440)
    webhook_base_url: str | None = None  # Base URL for webhook callbacks

    @field_validator("encryption_salt", mode="before")
    @classmethod
    def generate_encryption_salt(cls, v: str, info) -> str:
        """Generate encryption salt from secret_key if not provided."""
        if v:
            return v
        # Derive salt from secret_key
        secret_key = info.data.get("secret_key", "")
        if secret_key:
            return hashlib.sha256(f"{secret_key}-salt".encode()).hexdigest()[:32]
        return secrets.token_hex(16)

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def google_oauth_configured(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Settings are loaded once and cached. To reload, clear the cache:
    ```python
    get_settings.cache_clear()
    ```
    """
    return Settings()


def get_settings_uncached() -> Settings:
    """Get fresh settings without caching.

    Useful for testing when environment variables change.
    """
    return Settings()
