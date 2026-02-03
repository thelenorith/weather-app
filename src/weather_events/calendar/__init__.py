"""Calendar integration module.

Provides integration with Google Calendar for syncing events and updating
them with weather information.

## Features

- List user's calendars
- Sync events from selected calendars
- Update events with weather data
- Support for polling or webhook-based sync

## Google Calendar API

Uses the Google Calendar API v3:
- https://developers.google.com/calendar/api/v3/reference

## Sync Modes

1. **Polling**: Periodically check for changes using sync tokens
2. **Webhook**: Receive push notifications when events change
3. **Manual**: Only sync when user requests

## Event Processing

1. Fetch events from calendar
2. Filter based on rules (colors, keywords, etc.)
3. Extract location and geocode if needed
4. Fetch weather forecast for event time/location
5. Update event title/description with weather info
"""

from weather_events.calendar.google_calendar import (
    GoogleCalendarClient,
    CalendarInfo,
    CalendarEvent,
)
from weather_events.calendar.sync import (
    CalendarSyncService,
    SyncResult,
)

__all__ = [
    "GoogleCalendarClient",
    "CalendarInfo",
    "CalendarEvent",
    "CalendarSyncService",
    "SyncResult",
]
