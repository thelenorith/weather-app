"""FastAPI dependencies for authentication.

These dependencies can be used in route handlers to require authentication
and get the current user.

## Usage

```python
from fastapi import Depends
from weather_events.auth import get_current_user, require_admin
from weather_events.database import User

@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {"email": user.email, "name": user.name}

@app.get("/admin/users")
async def list_users(user: User = Depends(require_admin)):
    # Only admins can access this
    ...
```
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather_events.auth.session import SessionData, verify_session_token
from weather_events.config import get_settings
from weather_events.database.connection import get_db_session
from weather_events.database.models import User

logger = logging.getLogger(__name__)


async def get_session_data(
    session_cookie: str | None = Cookie(default=None, alias="weather_session"),
) -> SessionData | None:
    """Extract and verify session data from cookie.

    Returns None if no session or invalid session.
    """
    if not session_cookie:
        return None

    return verify_session_token(session_cookie)


async def get_current_user_optional(
    session: SessionData | None = Depends(get_session_data),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Get the current user if logged in, or None.

    Use this for routes that work with or without authentication.
    """
    if session is None:
        return None

    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == session.user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"Session for non-existent/inactive user: {session.user_id}")
        return None

    return user


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Get the current authenticated user.

    Raises 401 if not authenticated.
    Use this for routes that require authentication.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an admin.

    Raises 403 if not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user


def get_user_id_from_session(
    session: SessionData | None = Depends(get_session_data),
) -> uuid.UUID | None:
    """Get just the user ID from session without database lookup.

    Useful for lightweight checks where you don't need the full user object.
    """
    if session is None:
        return None
    return session.user_id
