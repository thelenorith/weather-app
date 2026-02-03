"""Session management using signed JWT tokens.

Sessions are stored as signed JWT tokens in HTTP-only cookies.
The tokens contain:
- User ID
- Session creation time
- Expiration time

## Security

- Tokens are signed with the application secret key
- Tokens expire after a configurable period (default: 7 days)
- Cookies are HTTP-only to prevent XSS access
- Cookies are Secure in production (HTTPS only)
- SameSite=Lax to prevent CSRF

## Token Structure

```json
{
  "sub": "user-uuid",
  "iat": 1234567890,
  "exp": 1235172690,
  "type": "session"
}
```
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from weather_events.config import get_settings

logger = logging.getLogger(__name__)

# JWT configuration
ALGORITHM = "HS256"
TOKEN_TYPE = "session"


@dataclass
class SessionData:
    """Data stored in the session token."""

    user_id: uuid.UUID
    created_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(timezone.utc) > self.expires_at


def create_session_token(
    user_id: uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed session token for a user.

    Args:
        user_id: The user's UUID
        expires_delta: Custom expiration time (or use default from settings)

    Returns:
        Signed JWT token string
    """
    settings = get_settings()

    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(seconds=settings.session_max_age_seconds)

    expires_at = now + expires_delta

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": TOKEN_TYPE,
    }

    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token


def verify_session_token(token: str) -> SessionData | None:
    """Verify and decode a session token.

    Args:
        token: The JWT token string

    Returns:
        SessionData if valid, None if invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
        )
    except JWTError as e:
        logger.debug(f"Session token verification failed: {e}")
        return None

    # Verify token type
    if payload.get("type") != TOKEN_TYPE:
        logger.debug("Invalid token type")
        return None

    # Extract data
    try:
        user_id = uuid.UUID(payload["sub"])
        created_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except (KeyError, ValueError) as e:
        logger.debug(f"Invalid token payload: {e}")
        return None

    session = SessionData(
        user_id=user_id,
        created_at=created_at,
        expires_at=expires_at,
    )

    # Check expiration (jose should handle this, but double-check)
    if session.is_expired:
        logger.debug("Session token expired")
        return None

    return session


def create_csrf_token(session_token: str) -> str:
    """Create a CSRF token linked to the session.

    The CSRF token is derived from the session token, so it changes
    when the session changes.

    Args:
        session_token: The session JWT

    Returns:
        CSRF token string
    """
    import hashlib

    settings = get_settings()

    # Create CSRF token by hashing session + secret
    data = f"{session_token}:{settings.secret_key}:csrf"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def verify_csrf_token(session_token: str, csrf_token: str) -> bool:
    """Verify a CSRF token against the session.

    Args:
        session_token: The session JWT
        csrf_token: The CSRF token to verify

    Returns:
        True if CSRF token is valid
    """
    expected = create_csrf_token(session_token)
    # Use constant-time comparison to prevent timing attacks
    import hmac

    return hmac.compare_digest(expected, csrf_token)
