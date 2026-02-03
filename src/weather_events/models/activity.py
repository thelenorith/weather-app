"""Activity models defining requirements and constraints for different activities."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from weather_events.models.event import EventType


class ActivityCategory(str, Enum):
    """High-level activity categories."""

    EXERCISE = "exercise"
    ASTRONOMY = "astronomy"
    OUTDOOR_RECREATION = "outdoor_recreation"
    OUTDOOR_WORK = "outdoor_work"
    TRAVEL = "travel"
    CUSTOM = "custom"


class TemperatureRange(BaseModel):
    """Temperature range constraints."""

    min_c: float | None = Field(default=None, description="Minimum temperature in Celsius")
    max_c: float | None = Field(default=None, description="Maximum temperature in Celsius")
    ideal_min_c: float | None = Field(
        default=None, description="Ideal minimum temperature in Celsius"
    )
    ideal_max_c: float | None = Field(
        default=None, description="Ideal maximum temperature in Celsius"
    )

    def is_acceptable(self, temp_c: float) -> bool:
        """Check if temperature is within acceptable range."""
        if self.min_c is not None and temp_c < self.min_c:
            return False
        if self.max_c is not None and temp_c > self.max_c:
            return False
        return True

    def is_ideal(self, temp_c: float) -> bool:
        """Check if temperature is within ideal range."""
        min_ok = self.ideal_min_c is None or temp_c >= self.ideal_min_c
        max_ok = self.ideal_max_c is None or temp_c <= self.ideal_max_c
        return min_ok and max_ok


class WindConstraints(BaseModel):
    """Wind constraints for an activity."""

    max_speed_ms: float | None = Field(
        default=None, description="Maximum acceptable wind speed in m/s"
    )
    max_gust_ms: float | None = Field(
        default=None, description="Maximum acceptable gust speed in m/s"
    )
    ideal_max_speed_ms: float | None = Field(
        default=None, description="Ideal maximum wind speed in m/s"
    )

    def is_acceptable(self, speed_ms: float, gust_ms: float | None = None) -> bool:
        """Check if wind conditions are acceptable."""
        if self.max_speed_ms is not None and speed_ms > self.max_speed_ms:
            return False
        if gust_ms and self.max_gust_ms is not None and gust_ms > self.max_gust_ms:
            return False
        return True


class CloudConstraints(BaseModel):
    """Cloud cover constraints for an activity."""

    max_total_percent: float | None = Field(
        default=None, ge=0, le=100, description="Maximum acceptable total cloud cover"
    )
    max_high_percent: float | None = Field(
        default=None, ge=0, le=100, description="Maximum high cloud cover"
    )
    ideal_max_total_percent: float | None = Field(
        default=None, ge=0, le=100, description="Ideal maximum cloud cover"
    )


class PrecipitationConstraints(BaseModel):
    """Precipitation constraints for an activity."""

    max_probability_percent: float | None = Field(
        default=None, ge=0, le=100, description="Maximum acceptable precipitation probability"
    )
    allow_light_rain: bool = Field(
        default=False, description="Whether light rain is acceptable"
    )
    allow_snow: bool = Field(
        default=False, description="Whether snow is acceptable"
    )


class SunConstraints(BaseModel):
    """Sun position constraints for an activity."""

    min_altitude_deg: float | None = Field(
        default=None, description="Minimum sun altitude in degrees"
    )
    max_altitude_deg: float | None = Field(
        default=None, description="Maximum sun altitude in degrees"
    )
    require_below_horizon: bool = Field(
        default=False, description="Require sun to be below horizon"
    )
    require_astronomical_twilight: bool = Field(
        default=False, description="Require astronomical twilight (sun < -18°)"
    )


class MoonConstraints(BaseModel):
    """Moon constraints for an activity."""

    max_illumination_percent: float | None = Field(
        default=None, ge=0, le=100, description="Maximum acceptable moon illumination"
    )
    require_below_horizon: bool = Field(
        default=False, description="Require moon to be below horizon"
    )


class SeeingConstraints(BaseModel):
    """Astronomical seeing constraints.

    Seeing is a measure of atmospheric turbulence affecting image quality.
    Lower values = better seeing.
    """

    max_arcsec: float | None = Field(
        default=None, description="Maximum seeing in arcseconds"
    )
    ideal_max_arcsec: float | None = Field(
        default=None, description="Ideal maximum seeing in arcseconds"
    )


class TransparencyConstraints(BaseModel):
    """Atmospheric transparency constraints.

    Transparency affects how clearly stars can be seen.
    Higher values = better transparency.
    """

    min_magnitude: float | None = Field(
        default=None, description="Minimum limiting magnitude"
    )
    ideal_min_magnitude: float | None = Field(
        default=None, description="Ideal minimum limiting magnitude"
    )


class ActivityRequirements(BaseModel):
    """Complete set of requirements for an activity."""

    # Basic weather
    temperature: TemperatureRange | None = Field(default=None)
    wind: WindConstraints | None = Field(default=None)
    clouds: CloudConstraints | None = Field(default=None)
    precipitation: PrecipitationConstraints | None = Field(default=None)

    # Visibility
    min_visibility_m: float | None = Field(
        default=None, description="Minimum visibility in meters"
    )

    # Sun/Moon (for astronomy)
    sun: SunConstraints | None = Field(default=None)
    moon: MoonConstraints | None = Field(default=None)

    # Astronomy-specific
    seeing: SeeingConstraints | None = Field(default=None)
    transparency: TransparencyConstraints | None = Field(default=None)

    # Safety
    max_uv_index: float | None = Field(
        default=None, description="Maximum acceptable UV index"
    )
    require_daylight: bool = Field(
        default=False, description="Require daylight hours"
    )
    require_darkness: bool = Field(
        default=False, description="Require darkness"
    )


class Activity(BaseModel):
    """An activity type with its requirements and preferences."""

    # Identity
    id: str = Field(..., description="Unique activity identifier")
    name: str = Field(..., description="Human-readable activity name")
    description: str | None = Field(default=None, description="Activity description")

    # Classification
    category: ActivityCategory = Field(..., description="Activity category")
    event_types: list[EventType] = Field(
        default_factory=list,
        description="Event types that map to this activity",
    )

    # Requirements
    requirements: ActivityRequirements = Field(
        default_factory=ActivityRequirements,
        description="Weather requirements for this activity",
    )

    # Metadata
    icon: str | None = Field(default=None, description="Icon/emoji for this activity")
    keywords: list[str] = Field(
        default_factory=list, description="Keywords for detecting this activity"
    )
    custom_data: dict[str, Any] | None = Field(
        default=None, description="Activity-specific custom data"
    )

    # User preferences
    enabled: bool = Field(default=True, description="Whether this activity is enabled")
    user_notes: str | None = Field(
        default=None, description="User notes about this activity"
    )


# Pre-defined activity templates
def create_running_activity() -> Activity:
    """Create a running activity with typical requirements."""
    return Activity(
        id="running",
        name="Running",
        category=ActivityCategory.EXERCISE,
        event_types=[EventType.RUNNING],
        requirements=ActivityRequirements(
            temperature=TemperatureRange(
                min_c=-15,  # Can run in cold with proper gear
                max_c=35,   # Heat safety limit
                ideal_min_c=10,
                ideal_max_c=20,
            ),
            wind=WindConstraints(
                max_speed_ms=15,  # ~34 mph
                ideal_max_speed_ms=7,  # ~15 mph
            ),
            precipitation=PrecipitationConstraints(
                max_probability_percent=50,
                allow_light_rain=True,
            ),
        ),
        icon="🏃",
        keywords=["run", "running", "jog", "jogging"],
    )


def create_cycling_activity() -> Activity:
    """Create a cycling activity with typical requirements."""
    return Activity(
        id="cycling",
        name="Cycling",
        category=ActivityCategory.EXERCISE,
        event_types=[EventType.CYCLING],
        requirements=ActivityRequirements(
            temperature=TemperatureRange(
                min_c=-5,
                max_c=38,
                ideal_min_c=15,
                ideal_max_c=28,
            ),
            wind=WindConstraints(
                max_speed_ms=12,  # Wind affects cycling more
                max_gust_ms=18,
                ideal_max_speed_ms=5,
            ),
            precipitation=PrecipitationConstraints(
                max_probability_percent=30,
                allow_light_rain=False,  # Rain on road is dangerous
            ),
        ),
        icon="🚴",
        keywords=["bike", "cycling", "bicycle", "ride"],
    )


def create_astronomy_activity() -> Activity:
    """Create an astronomy observing activity with typical requirements."""
    return Activity(
        id="astronomy",
        name="Astronomy Observing",
        category=ActivityCategory.ASTRONOMY,
        event_types=[EventType.ASTRONOMY, EventType.ASTROPHOTOGRAPHY],
        requirements=ActivityRequirements(
            temperature=TemperatureRange(
                min_c=-20,  # Can observe in very cold
                max_c=35,
            ),
            wind=WindConstraints(
                max_speed_ms=8,  # Wind shakes telescope
                max_gust_ms=12,
                ideal_max_speed_ms=4,
            ),
            clouds=CloudConstraints(
                max_total_percent=30,
                ideal_max_total_percent=10,
            ),
            precipitation=PrecipitationConstraints(
                max_probability_percent=10,  # Any rain is bad for equipment
                allow_light_rain=False,
            ),
            sun=SunConstraints(
                require_below_horizon=True,
                require_astronomical_twilight=True,
            ),
            moon=MoonConstraints(
                max_illumination_percent=50,  # For deep sky
            ),
        ),
        icon="🔭",
        keywords=["astronomy", "observing", "telescope", "stargazing"],
    )


def create_solar_observation_activity() -> Activity:
    """Create a solar observation/imaging activity."""
    return Activity(
        id="solar_observation",
        name="Solar Observation",
        category=ActivityCategory.ASTRONOMY,
        event_types=[EventType.SOLAR_OBSERVATION],
        requirements=ActivityRequirements(
            temperature=TemperatureRange(
                min_c=0,
                max_c=38,
            ),
            wind=WindConstraints(
                max_speed_ms=6,  # Need stability for imaging
                max_gust_ms=10,
                ideal_max_speed_ms=3,
            ),
            clouds=CloudConstraints(
                max_total_percent=20,
                ideal_max_total_percent=5,
            ),
            sun=SunConstraints(
                min_altitude_deg=20,  # Need sun reasonably high
            ),
        ),
        icon="☀️",
        keywords=["solar", "sun", "h-alpha", "sun imaging"],
    )


DEFAULT_ACTIVITIES = [
    create_running_activity(),
    create_cycling_activity(),
    create_astronomy_activity(),
    create_solar_observation_activity(),
]
