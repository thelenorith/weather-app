"""Calendar synchronization service.

Handles syncing events from calendars and updating them with weather data.

## Sync Process

1. Get events from calendar (full or incremental sync)
2. Filter events based on user rules
3. For each event needing weather:
   a. Extract/geocode location
   b. Fetch weather forecast
   c. Generate weather summary
   d. Update event title/description
4. Store sync state for incremental updates

## Sync Modes

- **poll**: Background task periodically syncs calendars
- **webhook**: Receive push notifications on changes
- **manual**: User triggers sync manually
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather_events.calendar.google_calendar import (
    CalendarEvent,
    GoogleCalendarClient,
)
from weather_events.database.encryption import decrypt_token
from weather_events.database.models import (
    CalendarSync,
    OAuthToken,
    SyncedEvent,
    User,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a calendar sync operation."""

    calendar_sync_id: uuid.UUID
    calendar_name: str
    events_found: int = 0
    events_created: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    events_processed: int = 0
    errors: list[str] = field(default_factory=list)
    sync_token: str | None = None
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class CalendarSyncService:
    """Service for synchronizing calendars.

    Example:
        ```python
        service = CalendarSyncService(db_session)

        # Sync a specific calendar
        result = await service.sync_calendar(calendar_sync_id)

        # Sync all due calendars
        results = await service.sync_due_calendars()
        ```
    """

    def __init__(self, db: AsyncSession):
        """Initialize the sync service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_calendar_client(
        self,
        user_id: uuid.UUID,
    ) -> GoogleCalendarClient | None:
        """Get a calendar client for a user.

        Args:
            user_id: User ID

        Returns:
            GoogleCalendarClient or None if no valid tokens
        """
        # Get OAuth token for Google
        result = await self.db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == "google",
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            logger.warning(f"No Google OAuth token for user {user_id}")
            return None

        # Decrypt tokens
        access_token = decrypt_token(token.access_token_encrypted)
        refresh_token = None
        if token.refresh_token_encrypted:
            refresh_token = decrypt_token(token.refresh_token_encrypted)

        return GoogleCalendarClient(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token.expires_at,
        )

    async def sync_calendar(
        self,
        calendar_sync_id: uuid.UUID,
        force_full_sync: bool = False,
    ) -> SyncResult:
        """Sync a single calendar.

        Args:
            calendar_sync_id: CalendarSync ID
            force_full_sync: Force full sync instead of incremental

        Returns:
            SyncResult with sync statistics
        """
        # Get calendar sync config
        result = await self.db.execute(
            select(CalendarSync).where(CalendarSync.id == calendar_sync_id)
        )
        calendar_sync = result.scalar_one_or_none()

        if not calendar_sync:
            return SyncResult(
                calendar_sync_id=calendar_sync_id,
                calendar_name="Unknown",
                errors=["Calendar sync configuration not found"],
            )

        sync_result = SyncResult(
            calendar_sync_id=calendar_sync_id,
            calendar_name=calendar_sync.calendar_name or calendar_sync.calendar_id,
        )

        # Get calendar client
        client = await self.get_calendar_client(calendar_sync.user_id)
        if not client:
            sync_result.errors.append("Could not get calendar client")
            return sync_result

        # Determine sync parameters
        sync_token = None if force_full_sync else calendar_sync.last_sync_token

        # Get events
        time_min = None
        time_max = None
        if not sync_token:
            # Full sync: get events from now to 30 days out
            time_min = datetime.now(timezone.utc)
            time_max = time_min + timedelta(days=30)

        try:
            events, next_sync_token = client.list_events(
                calendar_id=calendar_sync.calendar_id,
                time_min=time_min,
                time_max=time_max,
                sync_token=sync_token,
            )
        except Exception as e:
            logger.exception(f"Error listing events: {e}")
            sync_result.errors.append(f"Error listing events: {str(e)}")
            calendar_sync.sync_error = str(e)
            await self.db.commit()
            return sync_result

        sync_result.events_found = len(events)
        sync_result.sync_token = next_sync_token

        # Process events
        for event in events:
            try:
                await self._process_event(calendar_sync, event, sync_result)
            except Exception as e:
                logger.exception(f"Error processing event {event.id}: {e}")
                sync_result.errors.append(f"Error processing event {event.id}: {str(e)}")

        # Update sync state
        calendar_sync.last_sync_at = datetime.now(timezone.utc)
        calendar_sync.last_sync_token = next_sync_token
        calendar_sync.sync_error = None

        await self.db.commit()

        logger.info(
            f"Synced calendar {calendar_sync.calendar_name}: "
            f"{sync_result.events_found} found, "
            f"{sync_result.events_created} created, "
            f"{sync_result.events_updated} updated"
        )

        return sync_result

    async def _process_event(
        self,
        calendar_sync: CalendarSync,
        event: CalendarEvent,
        sync_result: SyncResult,
    ) -> None:
        """Process a single event from the calendar.

        Args:
            calendar_sync: Calendar sync configuration
            event: The calendar event
            sync_result: Result object to update
        """
        # Check if event already exists
        result = await self.db.execute(
            select(SyncedEvent).where(
                SyncedEvent.calendar_sync_id == calendar_sync.id,
                SyncedEvent.external_event_id == event.id,
            )
        )
        synced_event = result.scalar_one_or_none()

        # Handle deleted events
        if event.status == "cancelled":
            if synced_event:
                await self.db.delete(synced_event)
                sync_result.events_deleted += 1
            return

        # Filter event based on rules
        if not self._should_process_event(calendar_sync, event):
            return

        if synced_event:
            # Update existing
            self._update_synced_event(synced_event, event)
            sync_result.events_updated += 1
        else:
            # Create new
            synced_event = self._create_synced_event(calendar_sync, event)
            self.db.add(synced_event)
            sync_result.events_created += 1

        sync_result.events_processed += 1

    def _should_process_event(
        self,
        calendar_sync: CalendarSync,
        event: CalendarEvent,
    ) -> bool:
        """Check if an event should be processed based on filter rules.

        Args:
            calendar_sync: Calendar sync configuration
            event: The calendar event

        Returns:
            True if event should be processed
        """
        rules = calendar_sync.event_filter_rules or {}

        # Filter by color
        colors = rules.get("colors", [])
        if colors and event.color_id not in colors:
            return False

        # Filter by keywords in title
        keywords = rules.get("keywords", [])
        if keywords:
            title_lower = event.summary.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                return False

        # Require location if specified
        if rules.get("require_location", False):
            if not event.location:
                return False

        # Skip all-day events if specified
        if rules.get("skip_all_day", False):
            if event.is_all_day:
                return False

        return True

    def _create_synced_event(
        self,
        calendar_sync: CalendarSync,
        event: CalendarEvent,
    ) -> SyncedEvent:
        """Create a new SyncedEvent from a CalendarEvent."""
        return SyncedEvent(
            calendar_sync_id=calendar_sync.id,
            external_event_id=event.id,
            external_etag=event.etag,
            title=event.summary,
            original_title=event.summary,
            description=event.description,
            original_description=event.description,
            start_time=event.start or datetime.now(timezone.utc),
            end_time=event.end or datetime.now(timezone.utc),
            is_all_day=event.is_all_day,
            timezone=event.time_zone,
            location_text=event.location,
            event_color=event.color_id,
            is_processed=False,
        )

    def _update_synced_event(
        self,
        synced_event: SyncedEvent,
        event: CalendarEvent,
    ) -> None:
        """Update a SyncedEvent with new data from CalendarEvent."""
        synced_event.external_etag = event.etag
        synced_event.start_time = event.start or synced_event.start_time
        synced_event.end_time = event.end or synced_event.end_time
        synced_event.is_all_day = event.is_all_day
        synced_event.timezone = event.time_zone
        synced_event.location_text = event.location
        synced_event.event_color = event.color_id

        # Only update title if it hasn't been modified by us
        if synced_event.title == synced_event.original_title:
            synced_event.title = event.summary
            synced_event.original_title = event.summary

        # Mark for re-processing if location or time changed
        synced_event.is_processed = False

    async def sync_due_calendars(self) -> list[SyncResult]:
        """Sync all calendars that are due for sync.

        Returns:
            List of SyncResult for each calendar synced
        """
        # Find calendars due for sync
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(CalendarSync).where(
                CalendarSync.is_enabled == True,
                CalendarSync.sync_mode == "poll",
            )
        )
        calendars = result.scalars().all()

        results = []
        for calendar in calendars:
            # Check if due for sync
            if calendar.last_sync_at:
                next_sync = calendar.last_sync_at + timedelta(
                    minutes=calendar.poll_interval_minutes
                )
                if next_sync > now:
                    continue

            sync_result = await self.sync_calendar(calendar.id)
            results.append(sync_result)

        return results
