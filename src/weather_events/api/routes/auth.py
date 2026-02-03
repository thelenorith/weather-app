"""Authentication routes.

Handles Google OAuth login flow and session management.

## OAuth Flow

1. GET /auth/login - Redirect to Google consent screen
2. GET /auth/google/callback - Handle OAuth callback
3. POST /auth/logout - Clear session
4. GET /auth/me - Get current user info

## Session Management

Sessions are stored in HTTP-only cookies. The session token is a signed JWT
containing the user ID and expiration time.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather_events.auth.dependencies import get_current_user, get_current_user_optional
from weather_events.auth.google import GoogleOAuth, get_google_oauth
from weather_events.auth.session import create_session_token
from weather_events.config import get_settings
from weather_events.database.connection import get_db_session
from weather_events.database.encryption import encrypt_token
from weather_events.database.models import OAuthToken, User, UserSettings

logger = logging.getLogger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User information response."""

    id: str
    email: str
    name: str | None
    picture_url: str | None
    is_admin: bool


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    authenticated: bool
    user: UserResponse | None = None


# Store state tokens temporarily (in production, use Redis or similar)
_oauth_states: dict[str, datetime] = {}


def _generate_state() -> str:
    """Generate a random state token for OAuth."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.now(timezone.utc)
    return state


def _verify_state(state: str) -> bool:
    """Verify and consume a state token."""
    if state not in _oauth_states:
        return False

    created = _oauth_states.pop(state)
    # State tokens expire after 10 minutes
    age = (datetime.now(timezone.utc) - created).total_seconds()
    return age < 600


@router.get("/login")
async def login(
    oauth: GoogleOAuth = Depends(get_google_oauth),
) -> RedirectResponse:
    """Initiate Google OAuth login.

    Redirects the user to Google's consent screen. After consent,
    Google redirects back to /auth/google/callback.
    """
    if not oauth.is_configured:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured",
        )

    state = _generate_state()
    auth_url = oauth.get_authorization_url(state=state)

    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    response: Response,
    oauth: GoogleOAuth = Depends(get_google_oauth),
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    """Handle Google OAuth callback.

    Exchanges the authorization code for tokens, creates/updates the user,
    and sets the session cookie.
    """
    settings = get_settings()

    # Verify state
    if not _verify_state(state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )

    # Exchange code for tokens
    try:
        tokens = await oauth.exchange_code(code)
    except ValueError as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code",
        )

    # Get user info from Google
    try:
        user_info = await oauth.get_user_info(tokens.access_token)
    except ValueError as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user information",
        )

    # Find or create user
    result = await db.execute(
        select(User).where(User.google_id == user_info.id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        user.email = user_info.email
        user.name = user_info.name
        user.picture_url = user_info.picture
        user.last_login_at = datetime.now(timezone.utc)
    else:
        # Create new user
        user = User(
            google_id=user_info.id,
            email=user_info.email,
            name=user_info.name,
            picture_url=user_info.picture,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()  # Get user ID

        # Create default settings
        user_settings = UserSettings(user_id=user.id)
        db.add(user_settings)

    # Store OAuth token (encrypted)
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == "google",
        )
    )
    oauth_token = result.scalar_one_or_none()

    if oauth_token:
        # Update existing token
        oauth_token.access_token_encrypted = encrypt_token(tokens.access_token)
        if tokens.refresh_token:
            oauth_token.refresh_token_encrypted = encrypt_token(tokens.refresh_token)
        oauth_token.expires_at = tokens.expires_at
        oauth_token.scope = tokens.scope
    else:
        # Create new token
        oauth_token = OAuthToken(
            user_id=user.id,
            provider="google",
            provider_user_id=user_info.id,
            access_token_encrypted=encrypt_token(tokens.access_token),
            refresh_token_encrypted=(
                encrypt_token(tokens.refresh_token) if tokens.refresh_token else None
            ),
            token_type=tokens.token_type,
            scope=tokens.scope,
            expires_at=tokens.expires_at,
        )
        db.add(oauth_token)

    await db.commit()

    # Create session token
    session_token = create_session_token(user.id)

    # Set session cookie
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )

    logger.info(f"User {user.email} logged in")

    return redirect


@router.post("/logout")
async def logout(
    response: Response,
    user: User | None = Depends(get_current_user_optional),
) -> dict:
    """Log out the current user.

    Clears the session cookie.
    """
    settings = get_settings()

    if user:
        logger.info(f"User {user.email} logged out")

    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )

    return {"status": "logged_out"}


@router.get("/me", response_model=AuthStatusResponse)
async def get_auth_status(
    user: User | None = Depends(get_current_user_optional),
) -> AuthStatusResponse:
    """Get the current authentication status and user info."""
    if user:
        return AuthStatusResponse(
            authenticated=True,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name,
                picture_url=user.picture_url,
                is_admin=user.is_admin,
            ),
        )

    return AuthStatusResponse(authenticated=False)
