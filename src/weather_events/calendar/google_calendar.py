"""Google Calendar API client.

Provides methods for interacting with Google Calendar:
- List calendars
- List events
- Update events
- Watch for changes (webhooks)

## API Documentation

https://developers.google.com/calendar/api/v3/reference

## Authentication

Uses OAuth 2.0 access tokens obtained during user authentication.
Tokens are automatically refreshed when expired.

## Rate Limits

Google Calendar API has quotas:
- 1,000,000 queries per day (default)
- 500 queries per 100 seconds per user

Use incremental sync (sync tokens) to minimize API calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


@dataclass
class CalendarInfo:
    """Information about a calendar."""

    id: str
    summary: str
    description: str | None = None
    time_zone: str | None = None
    background_color: str | None = None
    foreground_color: str | None = None
    is_primary: bool = False
    access_role: str = "reader"  # reader, writer, owner

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CalendarInfo:
        """Create from Google Calendar API response."""
        return cls(
            id=data["id"],
            summary=data.get("summary", ""),
            description=data.get("description"),
            time_zone=data.get("timeZone"),
            background_color=data.get("backgroundColor"),
            foreground_color=data.get("foregroundColor"),
            is_primary=data.get("primary", False),
            access_role=data.get("accessRole", "reader"),
        )


@dataclass
class CalendarEvent:
    """A calendar event."""

    id: str
    calendar_id: str
    summary: str
    description: str | None = None
    location: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    start_date: str | None = None  # For all-day events (YYYY-MM-DD)
    end_date: str | None = None
    time_zone: str | None = None
    is_all_day: bool = False
    status: str = "confirmed"  # confirmed, tentative, cancelled
    color_id: str | None = None
    etag: str | None = None
    html_link: str | None = None
    attendees: list[dict[str, Any]] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict[str, Any], calendar_id: str) -> CalendarEvent:
        """Create from Google Calendar API response."""
        start_data = data.get("start", {})
        end_data = data.get("end", {})

        # Determine if all-day event
        is_all_day = "date" in start_data

        # Parse datetime
        start = None
        end = None
        start_date = None
        end_date = None

        if is_all_day:
            start_date = start_data.get("date")
            end_date = end_data.get("date")
        else:
            start_str = start_data.get("dateTime")
            end_str = end_data.get("dateTime")
            if start_str:
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            if end_str:
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            calendar_id=calendar_id,
            summary=data.get("summary", "(No title)"),
            description=data.get("description"),
            location=data.get("location"),
            start=start,
            end=end,
            start_date=start_date,
            end_date=end_date,
            time_zone=start_data.get("timeZone"),
            is_all_day=is_all_day,
            status=data.get("status", "confirmed"),
            color_id=data.get("colorId"),
            etag=data.get("etag"),
            html_link=data.get("htmlLink"),
            attendees=data.get("attendees", []),
            raw_data=data,
        )

    def to_update_body(self) -> dict[str, Any]:
        """Convert to API update body format."""
        body: dict[str, Any] = {
            "summary": self.summary,
        }

        if self.description is not None:
            body["description"] = self.description

        if self.location is not None:
            body["location"] = self.location

        return body


class GoogleCalendarClient:
    """Client for Google Calendar API.

    Example:
        ```python
        client = GoogleCalendarClient(access_token, refresh_token)

        # List calendars
        calendars = await client.list_calendars()

        # List events
        events = await client.list_events(calendar_id, time_min, time_max)

        # Update event
        await client.update_event(calendar_id, event_id, updates)
        ```
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        token_expiry: datetime | None = None,
    ):
        """Initialize the client.

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token for auto-refresh
            token_expiry: When the access token expires
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry

        # Create credentials
        self._credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,  # Will use default
            client_secret=None,
        )

        # Build service
        self._service = build("calendar", "v3", credentials=self._credentials)

    def list_calendars(self) -> list[CalendarInfo]:
        """List all calendars accessible to the user.

        Returns:
            List of CalendarInfo objects
        """
        calendars = []
        page_token = None

        while True:
            result = (
                self._service.calendarList()
                .list(pageToken=page_token)
                .execute()
            )

            for item in result.get("items", []):
                calendars.append(CalendarInfo.from_api(item))

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return calendars

    def list_events(
        self,
        calendar_id: str,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 250,
        sync_token: str | None = None,
    ) -> tuple[list[CalendarEvent], str | None]:
        """List events from a calendar.

        Args:
            calendar_id: Calendar ID (use 'primary' for primary calendar)
            time_min: Minimum start time (exclusive)
            time_max: Maximum start time (exclusive)
            max_results: Maximum events to return
            sync_token: Token for incremental sync

        Returns:
            Tuple of (events, next_sync_token)
        """
        events = []
        page_token = None
        next_sync_token = None

        params: dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,  # Expand recurring events
            "orderBy": "startTime",
        }

        if sync_token:
            params["syncToken"] = sync_token
        else:
            if time_min:
                params["timeMin"] = time_min.isoformat()
            if time_max:
                params["timeMax"] = time_max.isoformat()

        while True:
            if page_token:
                params["pageToken"] = page_token

            try:
                result = self._service.events().list(**params).execute()
            except HttpError as e:
                if e.resp.status == 410:
                    # Sync token expired, need full sync
                    logger.warning(
                        f"Sync token expired for calendar {calendar_id}, "
                        "performing full sync"
                    )
                    # Remove sync token and retry
                    params.pop("syncToken", None)
                    if time_min:
                        params["timeMin"] = time_min.isoformat()
                    result = self._service.events().list(**params).execute()
                else:
                    raise

            for item in result.get("items", []):
                # Skip cancelled events unless doing incremental sync
                if item.get("status") == "cancelled" and not sync_token:
                    continue
                events.append(CalendarEvent.from_api(item, calendar_id))

            page_token = result.get("nextPageToken")
            if not page_token:
                next_sync_token = result.get("nextSyncToken")
                break

        return events, next_sync_token

    def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent | None:
        """Get a single event by ID.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID

        Returns:
            CalendarEvent or None if not found
        """
        try:
            result = (
                self._service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )
            return CalendarEvent.from_api(result, calendar_id)
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: str | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> CalendarEvent:
        """Update an event.

        Only provided fields are updated. Use None to leave unchanged.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            summary: New title
            description: New description
            location: New location

        Returns:
            Updated CalendarEvent
        """
        # Get current event
        current = (
            self._service.events()
            .get(calendarId=calendar_id, eventId=event_id)
            .execute()
        )

        # Update fields
        if summary is not None:
            current["summary"] = summary
        if description is not None:
            current["description"] = description
        if location is not None:
            current["location"] = location

        # Patch event
        result = (
            self._service.events()
            .patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=current,
            )
            .execute()
        )

        return CalendarEvent.from_api(result, calendar_id)

    def watch_calendar(
        self,
        calendar_id: str,
        channel_id: str,
        webhook_url: str,
        token: str | None = None,
        expiration_hours: int = 24,
    ) -> dict[str, Any]:
        """Set up push notifications for a calendar.

        Args:
            calendar_id: Calendar ID to watch
            channel_id: Unique channel identifier
            webhook_url: URL to receive notifications
            token: Optional verification token
            expiration_hours: Hours until watch expires (max 24 for most)

        Returns:
            Watch response with resourceId and expiration
        """
        import time

        expiration_ms = int((time.time() + expiration_hours * 3600) * 1000)

        body = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_url,
            "expiration": expiration_ms,
        }

        if token:
            body["token"] = token

        result = (
            self._service.events()
            .watch(calendarId=calendar_id, body=body)
            .execute()
        )

        return result

    def stop_watch(self, channel_id: str, resource_id: str) -> None:
        """Stop watching a calendar.

        Args:
            channel_id: The channel ID from watch setup
            resource_id: The resource ID from watch response
        """
        self._service.channels().stop(
            body={
                "id": channel_id,
                "resourceId": resource_id,
            }
        ).execute()
