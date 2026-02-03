"""Google OAuth authentication.

Implements the OAuth 2.0 authorization code flow for Google sign-in.

## Required Setup

1. Create a project in Google Cloud Console
2. Enable Google Calendar API
3. Create OAuth 2.0 credentials (Web application)
4. Add authorized redirect URIs
5. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables

## OAuth Endpoints

- Authorization: https://accounts.google.com/o/oauth2/v2/auth
- Token: https://oauth2.googleapis.com/token
- User Info: https://www.googleapis.com/oauth2/v2/userinfo

## Scopes Used

- openid: Required for authentication
- email: Get user's email address
- profile: Get user's name and picture
- https://www.googleapis.com/auth/calendar.readonly: Read calendar data
- https://www.googleapis.com/auth/calendar.events: Modify events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import httpx
from authlib.integrations.starlette_client import OAuth

from weather_events.config import get_settings

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


@dataclass
class GoogleUserInfo:
    """User information from Google."""

    id: str
    email: str
    name: str | None
    picture: str | None
    verified_email: bool


@dataclass
class GoogleTokens:
    """OAuth tokens from Google."""

    access_token: str
    refresh_token: str | None
    token_type: str
    expires_at: datetime | None
    scope: str


class GoogleOAuth:
    """Google OAuth 2.0 client.

    Handles the OAuth flow and token management for Google sign-in.

    Example:
        ```python
        oauth = GoogleOAuth()

        # Generate authorization URL
        auth_url = oauth.get_authorization_url(state="random-state")
        # Redirect user to auth_url

        # Handle callback
        tokens = await oauth.exchange_code(code)
        user_info = await oauth.get_user_info(tokens.access_token)
        ```
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        scopes: list[str] | None = None,
    ):
        """Initialize Google OAuth client.

        Args:
            client_id: Google OAuth client ID (or from settings)
            client_secret: Google OAuth client secret (or from settings)
            redirect_uri: OAuth callback URL (or from settings)
            scopes: OAuth scopes to request (or from settings)
        """
        settings = get_settings()

        self.client_id = client_id or settings.google_client_id
        self.client_secret = client_secret or settings.google_client_secret
        self.redirect_uri = redirect_uri or settings.google_redirect_uri
        self.scopes = scopes or settings.google_calendar_scopes + [
            "openid",
            "email",
            "profile",
        ]

        if not self.client_id or not self.client_secret:
            logger.warning(
                "Google OAuth not configured. Set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET environment variables."
            )

    @property
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(
        self,
        state: str,
        access_type: str = "offline",
        prompt: str = "consent",
    ) -> str:
        """Generate the Google OAuth authorization URL.

        Args:
            state: Random state parameter for CSRF protection
            access_type: "offline" to get refresh token
            prompt: "consent" to always show consent screen

        Returns:
            URL to redirect the user to
        """
        if not self.is_configured:
            raise RuntimeError("Google OAuth not configured")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": access_type,
            "prompt": prompt,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTHORIZE_URL}?{query}"

    async def exchange_code(self, code: str) -> GoogleTokens:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback

        Returns:
            GoogleTokens with access and refresh tokens

        Raises:
            ValueError: If token exchange fails
        """
        if not self.is_configured:
            raise RuntimeError("Google OAuth not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + __import__("datetime").timedelta(seconds=data["expires_in"])

        return GoogleTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", ""),
        )

    async def refresh_access_token(self, refresh_token: str) -> GoogleTokens:
        """Refresh an expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New GoogleTokens (refresh_token may be the same)

        Raises:
            ValueError: If refresh fails
        """
        if not self.is_configured:
            raise RuntimeError("Google OAuth not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                raise ValueError(f"Token refresh failed: {response.status_code}")

            data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + __import__("datetime").timedelta(seconds=data["expires_in"])

        return GoogleTokens(
            access_token=data["access_token"],
            # Google may not return a new refresh token
            refresh_token=data.get("refresh_token", refresh_token),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", ""),
        )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user information from Google.

        Args:
            access_token: Valid access token

        Returns:
            GoogleUserInfo with user details

        Raises:
            ValueError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.error(f"User info request failed: {response.text}")
                raise ValueError(f"User info request failed: {response.status_code}")

            data = response.json()

        return GoogleUserInfo(
            id=data["id"],
            email=data["email"],
            name=data.get("name"),
            picture=data.get("picture"),
            verified_email=data.get("verified_email", False),
        )

    async def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token.

        Args:
            token: The token to revoke

        Returns:
            True if revocation succeeded
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_REVOKE_URL,
                params={"token": token},
            )

            return response.status_code == 200


@lru_cache
def get_google_oauth() -> GoogleOAuth:
    """Get cached Google OAuth client instance."""
    return GoogleOAuth()
