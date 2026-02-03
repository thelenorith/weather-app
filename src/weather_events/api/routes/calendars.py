"""Calendar management routes.

Handles listing, configuring, and syncing calendars.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather_events.auth.dependencies import get_current_user
from weather_events.calendar.google_calendar import CalendarInfo
from weather_events.calendar.sync import CalendarSyncService
from weather_events.database.connection import get_db_session
from weather_events.database.models import CalendarSync, User

router = APIRouter()


class CalendarInfoResponse(BaseModel):
    """Calendar information from provider."""

    id: str
    summary: str
    description: str | None
    time_zone: str | None
    background_color: str | None
    is_primary: bool
    access_role: str


class CalendarSyncResponse(BaseModel):
    """Calendar sync configuration."""

    id: str
    calendar_id: str
    calendar_name: str | None
    provider: str
    sync_mode: str
    is_enabled: bool
    poll_interval_minutes: int
    last_sync_at: datetime | None
    sync_error: str | None
    event_filter_rules: dict[str, Any] | None
    default_activity_type: str | None


class CalendarSyncCreate(BaseModel):
    """Create calendar sync request."""

    calendar_id: str
    calendar_name: str | None = None
    sync_mode: str = Field(default="poll", pattern="^(poll|webhook|manual)$")
    poll_interval_minutes: int = Field(default=15, ge=5, le=1440)
    event_filter_rules: dict[str, Any] | None = None
    default_activity_type: str | None = None


class CalendarSyncUpdate(BaseModel):
    """Update calendar sync request."""

    calendar_name: str | None = None
    sync_mode: str | None = Field(default=None, pattern="^(poll|webhook|manual)$")
    is_enabled: bool | None = None
    poll_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    event_filter_rules: dict[str, Any] | None = None
    default_activity_type: str | None = None


class SyncResultResponse(BaseModel):
    """Sync result response."""

    calendar_name: str
    events_found: int
    events_created: int
    events_updated: int
    events_deleted: int
    errors: list[str]
    synced_at: datetime


@router.get("/available", response_model=list[CalendarInfoResponse])
async def list_available_calendars(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[CalendarInfoResponse]:
    """List all calendars available from the user's Google account."""
    sync_service = CalendarSyncService(db)
    client = await sync_service.get_calendar_client(user.id)

    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google Calendar connection. Please reconnect your account.",
        )

    try:
        calendars = client.list_calendars()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch calendars: {str(e)}",
        )

    return [
        CalendarInfoResponse(
            id=c.id,
            summary=c.summary,
            description=c.description,
            time_zone=c.time_zone,
            background_color=c.background_color,
            is_primary=c.is_primary,
            access_role=c.access_role,
        )
        for c in calendars
    ]


@router.get("/", response_model=list[CalendarSyncResponse])
async def list_synced_calendars(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[CalendarSyncResponse]:
    """List all calendars configured for sync."""
    result = await db.execute(
        select(CalendarSync).where(CalendarSync.user_id == user.id)
    )
    calendars = result.scalars().all()

    return [
        CalendarSyncResponse(
            id=str(c.id),
            calendar_id=c.calendar_id,
            calendar_name=c.calendar_name,
            provider=c.provider,
            sync_mode=c.sync_mode,
            is_enabled=c.is_enabled,
            poll_interval_minutes=c.poll_interval_minutes,
            last_sync_at=c.last_sync_at,
            sync_error=c.sync_error,
            event_filter_rules=c.event_filter_rules,
            default_activity_type=c.default_activity_type,
        )
        for c in calendars
    ]


@router.post("/", response_model=CalendarSyncResponse, status_code=status.HTTP_201_CREATED)
async def add_calendar_sync(
    data: CalendarSyncCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CalendarSyncResponse:
    """Add a calendar to sync."""
    # Check if already syncing this calendar
    result = await db.execute(
        select(CalendarSync).where(
            CalendarSync.user_id == user.id,
            CalendarSync.provider == "google",
            CalendarSync.calendar_id == data.calendar_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Calendar is already configured for sync",
        )

    calendar_sync = CalendarSync(
        user_id=user.id,
        provider="google",
        calendar_id=data.calendar_id,
        calendar_name=data.calendar_name,
        sync_mode=data.sync_mode,
        poll_interval_minutes=data.poll_interval_minutes,
        event_filter_rules=data.event_filter_rules,
        default_activity_type=data.default_activity_type,
    )

    db.add(calendar_sync)
    await db.commit()
    await db.refresh(calendar_sync)

    return CalendarSyncResponse(
        id=str(calendar_sync.id),
        calendar_id=calendar_sync.calendar_id,
        calendar_name=calendar_sync.calendar_name,
        provider=calendar_sync.provider,
        sync_mode=calendar_sync.sync_mode,
        is_enabled=calendar_sync.is_enabled,
        poll_interval_minutes=calendar_sync.poll_interval_minutes,
        last_sync_at=calendar_sync.last_sync_at,
        sync_error=calendar_sync.sync_error,
        event_filter_rules=calendar_sync.event_filter_rules,
        default_activity_type=calendar_sync.default_activity_type,
    )


@router.patch("/{calendar_sync_id}", response_model=CalendarSyncResponse)
async def update_calendar_sync(
    calendar_sync_id: uuid.UUID,
    data: CalendarSyncUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CalendarSyncResponse:
    """Update calendar sync configuration."""
    result = await db.execute(
        select(CalendarSync).where(
            CalendarSync.id == calendar_sync_id,
            CalendarSync.user_id == user.id,
        )
    )
    calendar_sync = result.scalar_one_or_none()

    if not calendar_sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar sync configuration not found",
        )

    # Update fields
    if data.calendar_name is not None:
        calendar_sync.calendar_name = data.calendar_name
    if data.sync_mode is not None:
        calendar_sync.sync_mode = data.sync_mode
    if data.is_enabled is not None:
        calendar_sync.is_enabled = data.is_enabled
    if data.poll_interval_minutes is not None:
        calendar_sync.poll_interval_minutes = data.poll_interval_minutes
    if data.event_filter_rules is not None:
        calendar_sync.event_filter_rules = data.event_filter_rules
    if data.default_activity_type is not None:
        calendar_sync.default_activity_type = data.default_activity_type

    await db.commit()
    await db.refresh(calendar_sync)

    return CalendarSyncResponse(
        id=str(calendar_sync.id),
        calendar_id=calendar_sync.calendar_id,
        calendar_name=calendar_sync.calendar_name,
        provider=calendar_sync.provider,
        sync_mode=calendar_sync.sync_mode,
        is_enabled=calendar_sync.is_enabled,
        poll_interval_minutes=calendar_sync.poll_interval_minutes,
        last_sync_at=calendar_sync.last_sync_at,
        sync_error=calendar_sync.sync_error,
        event_filter_rules=calendar_sync.event_filter_rules,
        default_activity_type=calendar_sync.default_activity_type,
    )


@router.delete("/{calendar_sync_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_sync(
    calendar_sync_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a calendar from sync."""
    result = await db.execute(
        select(CalendarSync).where(
            CalendarSync.id == calendar_sync_id,
            CalendarSync.user_id == user.id,
        )
    )
    calendar_sync = result.scalar_one_or_none()

    if not calendar_sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar sync configuration not found",
        )

    await db.delete(calendar_sync)
    await db.commit()


@router.post("/{calendar_sync_id}/sync", response_model=SyncResultResponse)
async def sync_calendar(
    calendar_sync_id: uuid.UUID,
    force_full: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncResultResponse:
    """Manually trigger a calendar sync."""
    # Verify ownership
    result = await db.execute(
        select(CalendarSync).where(
            CalendarSync.id == calendar_sync_id,
            CalendarSync.user_id == user.id,
        )
    )
    calendar_sync = result.scalar_one_or_none()

    if not calendar_sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar sync configuration not found",
        )

    sync_service = CalendarSyncService(db)
    sync_result = await sync_service.sync_calendar(
        calendar_sync_id=calendar_sync_id,
        force_full_sync=force_full,
    )

    return SyncResultResponse(
        calendar_name=sync_result.calendar_name,
        events_found=sync_result.events_found,
        events_created=sync_result.events_created,
        events_updated=sync_result.events_updated,
        events_deleted=sync_result.events_deleted,
        errors=sync_result.errors,
        synced_at=sync_result.synced_at,
    )
