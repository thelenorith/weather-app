"""Authentication module for weather event recommendations.

Provides Google OAuth authentication and session management.

## OAuth Flow

1. User clicks "Login with Google"
2. Redirect to Google OAuth consent screen
3. Google redirects back with authorization code
4. Exchange code for access token and refresh token
5. Create/update user in database
6. Create session and set cookie

## Scopes

We request minimal scopes:
- openid: For authentication
- email: To identify the user
- profile: For display name and picture
- calendar.readonly: To read calendar events
- calendar.events: To update events with weather data

## Security

- All tokens are encrypted at rest
- Sessions use signed cookies
- HTTPS required in production
"""

from weather_events.auth.google import (
    GoogleOAuth,
    get_google_oauth,
)
from weather_events.auth.session import (
    create_session_token,
    verify_session_token,
    SessionData,
)
from weather_events.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
)

__all__ = [
    "GoogleOAuth",
    "get_google_oauth",
    "create_session_token",
    "verify_session_token",
    "SessionData",
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
]
