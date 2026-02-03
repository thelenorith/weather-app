"""Event models for calendar integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from weather_events.models.location import Location


class EventSource(str, Enum):
    """Source of the calendar event."""

    GOOGLE_CALENDAR = "google_calendar"
    ICAL = "ical"
    OUTLOOK = "outlook"
    MANUAL = "manual"
    APP_GENERATED = "app_generated"


class EventType(str, Enum):
    """Type/category of the event for rule matching."""

    # General outdoor
    OUTDOOR = "outdoor"

    # Exercise/sports
    RUNNING = "running"
    CYCLING = "cycling"
    HIKING = "hiking"
    SWIMMING = "swimming"
    SKIING = "skiing"
    GOLF = "golf"

    # Astronomy
    ASTRONOMY = "astronomy"
    ASTROPHOTOGRAPHY = "astrophotography"
    SOLAR_OBSERVATION = "solar_observation"
    METEOR_SHOWER = "meteor_shower"

    # Events/gatherings
    OUTDOOR_EVENT = "outdoor_event"
    PICNIC = "picnic"
    CAMPING = "camping"
    BARBECUE = "barbecue"

    # Work
    OUTDOOR_WORK = "outdoor_work"
    GARDENING = "gardening"

    # Other
    TRAVEL = "travel"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class EventTimeAdjustment(str, Enum):
    """How event times should be adjusted based on conditions."""

    NONE = "none"  # No adjustment
    ASTRONOMICAL_TWILIGHT = "astronomical_twilight"  # Start at astronomical twilight
    NAUTICAL_TWILIGHT = "nautical_twilight"  # Start at nautical twilight
    CIVIL_TWILIGHT = "civil_twilight"  # Start at civil twilight
    SUNSET = "sunset"  # Start at sunset
    SUNRISE = "sunrise"  # Start at sunrise
    SUNRISE_END = "sunrise_end"  # End at sunrise
    OPTIMAL_WINDOW = "optimal_window"  # Find optimal weather window
    SUN_ALTITUDE = "sun_altitude"  # Based on sun altitude threshold


class EventTimeConfig(BaseModel):
    """Configuration for event time adjustments."""

    adjustment_type: EventTimeAdjustment = Field(
        default=EventTimeAdjustment.NONE,
        description="Type of time adjustment to apply",
    )

    # For sun altitude adjustments
    min_sun_altitude_deg: float | None = Field(
        default=None, description="Minimum sun altitude in degrees"
    )
    max_sun_altitude_deg: float | None = Field(
        default=None, description="Maximum sun altitude in degrees"
    )

    # Duration preferences
    min_duration: timedelta | None = Field(
        default=None, description="Minimum event duration"
    )
    preferred_duration: timedelta | None = Field(
        default=None, description="Preferred event duration"
    )

    # Time window for optimal slot search
    search_window_start: datetime | None = Field(
        default=None, description="Start of window to search for optimal time"
    )
    search_window_end: datetime | None = Field(
        default=None, description="End of window to search for optimal time"
    )


class Event(BaseModel):
    """A calendar event that may have weather-related recommendations."""

    # Identity
    id: str | None = Field(default=None, description="Unique event identifier")
    source: EventSource = Field(
        default=EventSource.MANUAL, description="Source of this event"
    )
    external_id: str | None = Field(
        default=None, description="ID in the external calendar system"
    )

    # Basic event info
    title: str = Field(..., description="Event title")
    description: str | None = Field(default=None, description="Event description")

    # Time
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    all_day: bool = Field(default=False, description="Whether this is an all-day event")
    timezone: str | None = Field(
        default=None, description="Timezone for the event"
    )

    # Location
    location: Location | None = Field(default=None, description="Event location")

    # Classification
    event_type: EventType = Field(
        default=EventType.UNKNOWN, description="Type of event for rule matching"
    )
    calendar_name: str | None = Field(
        default=None, description="Name of the calendar this event is on"
    )
    color: str | None = Field(
        default=None, description="Calendar color code/name"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags/labels for the event"
    )

    # Time adjustment configuration
    time_config: EventTimeConfig | None = Field(
        default=None, description="Configuration for time adjustments"
    )

    # Weather annotation
    original_title: str | None = Field(
        default=None, description="Original title before weather annotation"
    )
    original_description: str | None = Field(
        default=None, description="Original description before weather annotation"
    )

    # Metadata
    guests: list[str] = Field(
        default_factory=list, description="List of guest email addresses"
    )
    created_at: datetime | None = Field(
        default=None, description="When the event was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="When the event was last updated"
    )
    raw_data: dict[str, Any] | None = Field(
        default=None, description="Raw data from calendar provider"
    )

    @property
    def duration(self) -> timedelta:
        """Get the event duration."""
        return self.end_time - self.start_time

    @property
    def duration_hours(self) -> float:
        """Get the event duration in hours."""
        return self.duration.total_seconds() / 3600

    def spans_multiple_hours(self) -> bool:
        """Check if event spans more than one hour."""
        return self.duration > timedelta(hours=1)

    def is_outdoor(self) -> bool:
        """Check if this event is likely an outdoor activity."""
        outdoor_types = {
            EventType.OUTDOOR,
            EventType.RUNNING,
            EventType.CYCLING,
            EventType.HIKING,
            EventType.SWIMMING,
            EventType.SKIING,
            EventType.GOLF,
            EventType.ASTRONOMY,
            EventType.ASTROPHOTOGRAPHY,
            EventType.SOLAR_OBSERVATION,
            EventType.METEOR_SHOWER,
            EventType.OUTDOOR_EVENT,
            EventType.PICNIC,
            EventType.CAMPING,
            EventType.BARBECUE,
            EventType.OUTDOOR_WORK,
            EventType.GARDENING,
        }
        return self.event_type in outdoor_types

    def needs_weather_forecast(self) -> bool:
        """Check if this event needs a weather forecast."""
        return self.location is not None and self.is_outdoor()

    def get_forecast_hours(self) -> list[datetime]:
        """Get the list of hours to fetch forecasts for."""
        hours = []
        current = self.start_time.replace(minute=0, second=0, microsecond=0)
        while current <= self.end_time:
            hours.append(current)
            current += timedelta(hours=1)
        return hours


# Keywords for detecting event types from titles/descriptions
EVENT_TYPE_KEYWORDS: dict[EventType, list[str]] = {
    EventType.RUNNING: ["run", "running", "jog", "jogging", "marathon", "5k", "10k"],
    EventType.CYCLING: ["bike", "biking", "cycling", "bicycle", "ride", "cycling"],
    EventType.HIKING: ["hike", "hiking", "trail", "backpacking"],
    EventType.SWIMMING: ["swim", "swimming", "pool", "lap"],
    EventType.SKIING: ["ski", "skiing", "snowboard", "slopes"],
    EventType.GOLF: ["golf", "golfing", "tee time"],
    EventType.ASTRONOMY: [
        "astronomy", "stargazing", "observing", "telescope", "stars",
        "deep sky", "nebula", "galaxy",
    ],
    EventType.ASTROPHOTOGRAPHY: [
        "astrophotography", "astro imaging", "deep sky imaging",
    ],
    EventType.SOLAR_OBSERVATION: [
        "solar", "sun observation", "sun imaging", "h-alpha",
    ],
    EventType.METEOR_SHOWER: [
        "meteor", "perseids", "geminids", "leonids", "shooting stars",
    ],
    EventType.OUTDOOR_EVENT: ["outdoor event", "festival", "concert outdoor"],
    EventType.PICNIC: ["picnic"],
    EventType.CAMPING: ["camping", "campsite", "tent"],
    EventType.BARBECUE: ["bbq", "barbecue", "grill", "cookout"],
    EventType.GARDENING: ["garden", "gardening", "yard work", "lawn"],
}


def detect_event_type(
    title: str,
    description: str | None = None,
    calendar_name: str | None = None,
) -> EventType:
    """Detect event type from title, description, and calendar name."""
    text = f"{title} {description or ''} {calendar_name or ''}".lower()

    # Check for astronomy calendar first (special case)
    if calendar_name and "astronomy" in calendar_name.lower():
        return EventType.ASTRONOMY

    # Check keywords
    for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return event_type

    # Check for generic outdoor indicators
    outdoor_keywords = ["outdoor", "outside", "park", "trail", "beach"]
    for keyword in outdoor_keywords:
        if keyword in text:
            return EventType.OUTDOOR

    return EventType.UNKNOWN
