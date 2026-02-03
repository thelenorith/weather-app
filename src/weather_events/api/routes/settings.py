"""User settings routes.

Handles user preferences and configuration.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather_events.auth.dependencies import get_current_user
from weather_events.database.connection import get_db_session
from weather_events.database.models import User, UserSettings

router = APIRouter()


class LocationSettings(BaseModel):
    """Location preferences."""

    default_location_name: str | None = None
    default_latitude: float | None = Field(default=None, ge=-90, le=90)
    default_longitude: float | None = Field(default=None, ge=-180, le=180)
    default_timezone: str | None = None


class UnitSettings(BaseModel):
    """Unit preferences."""

    temperature_unit: str = Field(default="celsius", pattern="^(celsius|fahrenheit)$")
    wind_speed_unit: str = Field(default="ms", pattern="^(ms|mph|kph)$")
    distance_unit: str = Field(default="km", pattern="^(km|miles)$")


class SyncSettings(BaseModel):
    """Calendar sync preferences."""

    default_sync_mode: str = Field(default="poll", pattern="^(poll|webhook|manual)$")
    poll_interval_minutes: int = Field(default=15, ge=5, le=1440)
    sync_enabled: bool = True


class DisplaySettings(BaseModel):
    """Display preferences."""

    title_delimiter: str = Field(default="|", max_length=16)
    description_delimiter: str = Field(default="---", max_length=16)
    prepend_weather_to_title: bool = True
    use_emoji: bool = True


class WeatherSettings(BaseModel):
    """Weather provider settings."""

    preferred_weather_provider: str = "metno"
    # API key would be set separately via a secure endpoint


class UserSettingsResponse(BaseModel):
    """Complete user settings response."""

    location: LocationSettings
    units: UnitSettings
    sync: SyncSettings
    display: DisplaySettings
    weather: WeatherSettings
    notifications_enabled: bool
    notification_email: str | None


class UserSettingsUpdate(BaseModel):
    """Update user settings request."""

    location: LocationSettings | None = None
    units: UnitSettings | None = None
    sync: SyncSettings | None = None
    display: DisplaySettings | None = None
    weather: WeatherSettings | None = None
    notifications_enabled: bool | None = None
    notification_email: str | None = None


@router.get("/", response_model=UserSettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserSettingsResponse:
    """Get the current user's settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return UserSettingsResponse(
        location=LocationSettings(
            default_location_name=settings.default_location_name,
            default_latitude=settings.default_latitude,
            default_longitude=settings.default_longitude,
            default_timezone=settings.default_timezone,
        ),
        units=UnitSettings(
            temperature_unit=settings.temperature_unit,
            wind_speed_unit=settings.wind_speed_unit,
            distance_unit=settings.distance_unit,
        ),
        sync=SyncSettings(
            default_sync_mode=settings.default_sync_mode,
            poll_interval_minutes=settings.poll_interval_minutes,
            sync_enabled=settings.sync_enabled,
        ),
        display=DisplaySettings(
            title_delimiter=settings.title_delimiter,
            description_delimiter=settings.description_delimiter,
            prepend_weather_to_title=settings.prepend_weather_to_title,
            use_emoji=settings.use_emoji,
        ),
        weather=WeatherSettings(
            preferred_weather_provider=settings.preferred_weather_provider,
        ),
        notifications_enabled=settings.notifications_enabled,
        notification_email=settings.notification_email,
    )


@router.patch("/", response_model=UserSettingsResponse)
async def update_settings(
    data: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserSettingsResponse:
    """Update the current user's settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    # Update location settings
    if data.location:
        if data.location.default_location_name is not None:
            settings.default_location_name = data.location.default_location_name
        if data.location.default_latitude is not None:
            settings.default_latitude = data.location.default_latitude
        if data.location.default_longitude is not None:
            settings.default_longitude = data.location.default_longitude
        if data.location.default_timezone is not None:
            settings.default_timezone = data.location.default_timezone

    # Update unit settings
    if data.units:
        settings.temperature_unit = data.units.temperature_unit
        settings.wind_speed_unit = data.units.wind_speed_unit
        settings.distance_unit = data.units.distance_unit

    # Update sync settings
    if data.sync:
        settings.default_sync_mode = data.sync.default_sync_mode
        settings.poll_interval_minutes = data.sync.poll_interval_minutes
        settings.sync_enabled = data.sync.sync_enabled

    # Update display settings
    if data.display:
        settings.title_delimiter = data.display.title_delimiter
        settings.description_delimiter = data.display.description_delimiter
        settings.prepend_weather_to_title = data.display.prepend_weather_to_title
        settings.use_emoji = data.display.use_emoji

    # Update weather settings
    if data.weather:
        settings.preferred_weather_provider = data.weather.preferred_weather_provider

    # Update notification settings
    if data.notifications_enabled is not None:
        settings.notifications_enabled = data.notifications_enabled
    if data.notification_email is not None:
        settings.notification_email = data.notification_email

    await db.commit()
    await db.refresh(settings)

    return UserSettingsResponse(
        location=LocationSettings(
            default_location_name=settings.default_location_name,
            default_latitude=settings.default_latitude,
            default_longitude=settings.default_longitude,
            default_timezone=settings.default_timezone,
        ),
        units=UnitSettings(
            temperature_unit=settings.temperature_unit,
            wind_speed_unit=settings.wind_speed_unit,
            distance_unit=settings.distance_unit,
        ),
        sync=SyncSettings(
            default_sync_mode=settings.default_sync_mode,
            poll_interval_minutes=settings.poll_interval_minutes,
            sync_enabled=settings.sync_enabled,
        ),
        display=DisplaySettings(
            title_delimiter=settings.title_delimiter,
            description_delimiter=settings.description_delimiter,
            prepend_weather_to_title=settings.prepend_weather_to_title,
            use_emoji=settings.use_emoji,
        ),
        weather=WeatherSettings(
            preferred_weather_provider=settings.preferred_weather_provider,
        ),
        notifications_enabled=settings.notifications_enabled,
        notification_email=settings.notification_email,
    )
