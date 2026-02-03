"""Database models for weather event recommendations.

## Security Notes

- OAuth tokens are encrypted at rest using Fernet symmetric encryption
- The encryption key is derived from the application secret
- PostgreSQL should be configured with SSL and disk encryption
- User emails are stored but can be hashed if anonymity is required

## Schema Overview

```
users
├── user_settings (1:1)
├── oauth_tokens (1:N) - encrypted
├── calendar_syncs (1:N)
│   └── synced_events (1:N)
├── activity_configs (1:N)
│   └── gear_rules (1:N)
```
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for all database models."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
    }


class SyncMode(str, Enum):
    """Calendar synchronization mode."""

    POLL = "poll"  # Periodic polling for changes
    WEBHOOK = "webhook"  # Push notifications via webhooks
    MANUAL = "manual"  # Manual refresh only


class User(Base):
    """User account model.

    Users are created via Google OAuth. The google_id is the primary
    identifier from Google, while we maintain our own UUID for internal use.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String(512))

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    oauth_tokens: Mapped[list["OAuthToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    calendar_syncs: Mapped[list["CalendarSync"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    activity_configs: Mapped[list["ActivityConfig"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserSettings(Base):
    """User preferences and settings.

    All configuration that affects how the app behaves for a specific user.
    """

    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    # Location preferences
    default_location_name: Mapped[str | None] = mapped_column(String(255))
    default_latitude: Mapped[float | None] = mapped_column(Float)
    default_longitude: Mapped[float | None] = mapped_column(Float)
    default_timezone: Mapped[str | None] = mapped_column(String(64))

    # Unit preferences
    temperature_unit: Mapped[str] = mapped_column(
        String(16), default="celsius"
    )  # celsius, fahrenheit
    wind_speed_unit: Mapped[str] = mapped_column(
        String(16), default="ms"
    )  # ms, mph, kph
    distance_unit: Mapped[str] = mapped_column(
        String(16), default="km"
    )  # km, miles

    # Weather provider preference
    preferred_weather_provider: Mapped[str] = mapped_column(
        String(32), default="metno"
    )
    weather_provider_api_key: Mapped[str | None] = mapped_column(
        Text
    )  # Encrypted in application layer

    # Calendar sync preferences
    default_sync_mode: Mapped[str] = mapped_column(String(16), default="poll")
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Notification preferences
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_email: Mapped[str | None] = mapped_column(String(255))

    # Display preferences
    title_delimiter: Mapped[str] = mapped_column(String(16), default="|")
    description_delimiter: Mapped[str] = mapped_column(String(16), default="---")
    prepend_weather_to_title: Mapped[bool] = mapped_column(Boolean, default=True)
    use_emoji: Mapped[bool] = mapped_column(Boolean, default=True)

    # Additional settings as JSON
    extra_settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id}>"


class OAuthToken(Base):
    """OAuth tokens for external services.

    Tokens are encrypted at rest. The encryption happens in the repository layer,
    not at the database level, to allow for key rotation.
    """

    __tablename__ = "oauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Provider identification
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # google, etc.
    provider_user_id: Mapped[str | None] = mapped_column(String(255))

    # Tokens (encrypted)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    token_type: Mapped[str] = mapped_column(String(32), default="Bearer")

    # Token metadata
    scope: Mapped[str | None] = mapped_column(Text)  # Space-separated scopes
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="oauth_tokens")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
        Index("ix_oauth_tokens_user_provider", "user_id", "provider"),
    )

    def __repr__(self) -> str:
        return f"<OAuthToken provider={self.provider} user_id={self.user_id}>"


class CalendarSync(Base):
    """Calendar synchronization configuration.

    Each user can sync multiple calendars. Each calendar can have different
    sync settings and rules for which events to process.
    """

    __tablename__ = "calendar_syncs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Calendar identification
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # google
    calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    calendar_name: Mapped[str | None] = mapped_column(String(255))

    # Sync configuration
    sync_mode: Mapped[str] = mapped_column(String(16), default="poll")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)

    # Webhook configuration (if sync_mode == webhook)
    webhook_channel_id: Mapped[str | None] = mapped_column(String(255))
    webhook_resource_id: Mapped[str | None] = mapped_column(String(255))
    webhook_expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Event filtering rules
    event_filter_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Example: {"colors": ["blue", "green"], "keywords": ["outdoor", "run"]}

    # Activity type mapping (what activity type events on this calendar default to)
    default_activity_type: Mapped[str | None] = mapped_column(String(64))

    # Sync state
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_token: Mapped[str | None] = mapped_column(
        Text
    )  # For incremental sync
    sync_error: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="calendar_syncs")
    synced_events: Mapped[list["SyncedEvent"]] = relationship(
        back_populates="calendar_sync", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider", "calendar_id", name="uq_user_calendar"
        ),
        Index("ix_calendar_syncs_user", "user_id"),
        Index("ix_calendar_syncs_next_poll", "is_enabled", "last_sync_at"),
    )

    def __repr__(self) -> str:
        return f"<CalendarSync {self.calendar_name or self.calendar_id}>"


class SyncedEvent(Base):
    """A calendar event that has been synced and processed.

    Stores the original event data and the weather-enhanced version.
    """

    __tablename__ = "synced_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    calendar_sync_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendar_syncs.id", ondelete="CASCADE")
    )

    # External event identification
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_etag: Mapped[str | None] = mapped_column(String(255))

    # Event data
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    original_title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    original_description: Mapped[str | None] = mapped_column(Text)

    # Time
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str | None] = mapped_column(String(64))

    # Location
    location_text: Mapped[str | None] = mapped_column(String(512))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Classification
    detected_activity_type: Mapped[str | None] = mapped_column(String(64))
    event_color: Mapped[str | None] = mapped_column(String(32))

    # Weather data
    weather_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    weather_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    weather_summary: Mapped[str | None] = mapped_column(String(255))

    # Processing state
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_error: Mapped[str | None] = mapped_column(Text)
    needs_time_adjustment: Mapped[bool] = mapped_column(Boolean, default=False)
    adjusted_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adjusted_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    calendar_sync: Mapped["CalendarSync"] = relationship(back_populates="synced_events")

    __table_args__ = (
        UniqueConstraint(
            "calendar_sync_id", "external_event_id", name="uq_sync_event"
        ),
        Index("ix_synced_events_calendar", "calendar_sync_id"),
        Index("ix_synced_events_time", "start_time", "end_time"),
        Index("ix_synced_events_needs_update", "is_processed", "weather_updated_at"),
    )

    def __repr__(self) -> str:
        return f"<SyncedEvent {self.title[:30]}>"


class ActivityConfig(Base):
    """User-specific activity configuration.

    Allows users to customize requirements and rules for each activity type.
    """

    __tablename__ = "activity_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Activity identification
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(16))  # Emoji
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Detection keywords (for auto-classifying events)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB)

    # Weather requirements (overrides defaults)
    requirements: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Example: {"temperature": {"min_c": 5, "max_c": 30}, "wind": {"max_speed_ms": 10}}

    # Time adjustment settings
    time_adjustment_type: Mapped[str | None] = mapped_column(String(64))
    time_adjustment_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="activity_configs")
    gear_rules: Mapped[list["GearRule"]] = relationship(
        back_populates="activity_config", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "activity_type", name="uq_user_activity"),
        Index("ix_activity_configs_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<ActivityConfig {self.activity_type}>"


class GearRule(Base):
    """User-specific gear recommendation rules.

    Allows users to customize what gear is recommended at what conditions.
    """

    __tablename__ = "gear_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_configs.id", ondelete="CASCADE")
    )

    # Gear item
    item_name: Mapped[str] = mapped_column(String(128), nullable=False)
    item_category: Mapped[str] = mapped_column(String(64), nullable=False)
    item_description: Mapped[str | None] = mapped_column(String(255))

    # Conditions (stored as JSON for flexibility)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Example: {"min_temp_c": null, "max_temp_c": 10, "min_wind_ms": null}

    # Rule settings
    priority: Mapped[int] = mapped_column(Integer, default=5)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    activity_config: Mapped["ActivityConfig"] = relationship(back_populates="gear_rules")

    __table_args__ = (
        Index("ix_gear_rules_activity", "activity_config_id"),
    )

    def __repr__(self) -> str:
        return f"<GearRule {self.item_name}>"
