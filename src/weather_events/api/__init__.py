"""FastAPI application and routes.

This module provides the REST API for the weather event recommendations service.

## API Structure

- /auth - Authentication endpoints (Google OAuth)
- /api/users - User management
- /api/calendars - Calendar sync configuration
- /api/activities - Activity configuration
- /api/settings - User settings
- /api/weather - Weather forecasts

## Authentication

Most endpoints require authentication via session cookie.
Sessions are created during OAuth login.

## Security

- All communication should be over HTTPS in production
- CSRF protection on state-changing endpoints
- Rate limiting on public endpoints
"""

from weather_events.api.app import create_app

__all__ = ["create_app"]
