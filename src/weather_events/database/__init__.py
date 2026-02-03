"""Database module for weather event recommendations.

This module provides:
- SQLAlchemy async database connection
- User, configuration, and calendar sync models
- Encrypted storage for sensitive data (OAuth tokens)
- Migration support via Alembic
"""

from weather_events.database.connection import (
    get_db,
    init_db,
    close_db,
    DatabaseSession,
)
from weather_events.database.models import (
    Base,
    User,
    UserSettings,
    OAuthToken,
    CalendarSync,
    SyncedEvent,
    ActivityConfig,
    GearRule as GearRuleModel,
)

__all__ = [
    # Connection
    "get_db",
    "init_db",
    "close_db",
    "DatabaseSession",
    # Models
    "Base",
    "User",
    "UserSettings",
    "OAuthToken",
    "CalendarSync",
    "SyncedEvent",
    "ActivityConfig",
    "GearRuleModel",
]
