"""Weather and forecast models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from weather_events.models.location import Coordinates


class WeatherCondition(str, Enum):
    """General weather condition categories."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    FOG = "fog"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    DRIZZLE = "drizzle"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    LIGHT_SNOW = "light_snow"
    HEAVY_SNOW = "heavy_snow"
    SLEET = "sleet"
    HAIL = "hail"
    WINDY = "windy"
    UNKNOWN = "unknown"


class CloudCover(BaseModel):
    """Cloud cover information."""

    total_percent: float = Field(
        ..., ge=0, le=100, description="Total cloud cover percentage"
    )
    low_percent: float | None = Field(
        default=None, ge=0, le=100, description="Low cloud cover percentage"
    )
    mid_percent: float | None = Field(
        default=None, ge=0, le=100, description="Mid-level cloud cover percentage"
    )
    high_percent: float | None = Field(
        default=None, ge=0, le=100, description="High cloud cover percentage"
    )

    def is_clear(self, threshold: float = 20.0) -> bool:
        """Check if sky is considered clear (below threshold)."""
        return self.total_percent <= threshold

    def is_mostly_clear(self, threshold: float = 40.0) -> bool:
        """Check if sky is mostly clear."""
        return self.total_percent <= threshold


class Precipitation(BaseModel):
    """Precipitation information."""

    probability_percent: float = Field(
        ..., ge=0, le=100, description="Probability of precipitation (%)"
    )
    amount_mm: float | None = Field(
        default=None, ge=0, description="Expected precipitation amount in mm"
    )
    type: str | None = Field(
        default=None, description="Type of precipitation (rain, snow, sleet, etc.)"
    )


class Wind(BaseModel):
    """Wind information."""

    speed_ms: float = Field(..., ge=0, description="Wind speed in meters per second")
    gust_ms: float | None = Field(
        default=None, ge=0, description="Wind gust speed in meters per second"
    )
    direction_deg: float | None = Field(
        default=None, ge=0, lt=360, description="Wind direction in degrees (0=N, 90=E)"
    )

    @property
    def speed_mph(self) -> float:
        """Wind speed in miles per hour."""
        return self.speed_ms * 2.237

    @property
    def speed_kph(self) -> float:
        """Wind speed in kilometers per hour."""
        return self.speed_ms * 3.6

    @property
    def gust_mph(self) -> float | None:
        """Wind gust speed in miles per hour."""
        return self.gust_ms * 2.237 if self.gust_ms else None

    @property
    def gust_kph(self) -> float | None:
        """Wind gust speed in kilometers per hour."""
        return self.gust_ms * 3.6 if self.gust_ms else None

    def direction_cardinal(self) -> str | None:
        """Get cardinal direction (N, NE, E, etc.)."""
        if self.direction_deg is None:
            return None
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(self.direction_deg / 22.5) % 16
        return directions[index]


class AstronomicalData(BaseModel):
    """Astronomical data for a location and time."""

    sunrise: datetime | None = Field(default=None, description="Sunrise time (sun at 0° altitude)")
    sunset: datetime | None = Field(default=None, description="Sunset time (sun at 0° altitude)")
    solar_noon: datetime | None = Field(default=None, description="Solar noon time")

    # Twilight times
    civil_twilight_start: datetime | None = Field(
        default=None, description="Civil twilight start (sun at -6°)"
    )
    civil_twilight_end: datetime | None = Field(
        default=None, description="Civil twilight end (sun at -6°)"
    )
    nautical_twilight_start: datetime | None = Field(
        default=None, description="Nautical twilight start (sun at -12°)"
    )
    nautical_twilight_end: datetime | None = Field(
        default=None, description="Nautical twilight end (sun at -12°)"
    )
    astronomical_twilight_start: datetime | None = Field(
        default=None, description="Astronomical twilight start (sun at -18°)"
    )
    astronomical_twilight_end: datetime | None = Field(
        default=None, description="Astronomical twilight end (sun at -18°)"
    )

    # Sun position
    sun_altitude_deg: float | None = Field(
        default=None, description="Sun altitude in degrees above horizon"
    )
    sun_azimuth_deg: float | None = Field(
        default=None, description="Sun azimuth in degrees (0=N, 90=E)"
    )

    # Moon data
    moonrise: datetime | None = Field(default=None, description="Moonrise time")
    moonset: datetime | None = Field(default=None, description="Moonset time")
    moon_phase: float | None = Field(
        default=None, ge=0, le=1, description="Moon phase (0=new, 0.5=full, 1=new)"
    )
    moon_illumination_percent: float | None = Field(
        default=None, ge=0, le=100, description="Moon illumination percentage"
    )
    moon_altitude_deg: float | None = Field(
        default=None, description="Moon altitude in degrees above horizon"
    )

    def is_night(self) -> bool | None:
        """Check if it's nighttime (sun below horizon)."""
        if self.sun_altitude_deg is None:
            return None
        return self.sun_altitude_deg < 0

    def is_astronomical_night(self) -> bool | None:
        """Check if it's astronomical night (sun below -18°)."""
        if self.sun_altitude_deg is None:
            return None
        return self.sun_altitude_deg < -18


class HourlyForecast(BaseModel):
    """Weather forecast for a single hour."""

    time: datetime = Field(..., description="Forecast time (start of hour)")
    condition: WeatherCondition = Field(
        default=WeatherCondition.UNKNOWN, description="General weather condition"
    )

    # Temperature
    temperature_c: float = Field(..., description="Temperature in Celsius")
    feels_like_c: float | None = Field(
        default=None, description="Feels-like temperature in Celsius"
    )
    dew_point_c: float | None = Field(
        default=None, description="Dew point in Celsius"
    )

    # Humidity
    relative_humidity_percent: float | None = Field(
        default=None, ge=0, le=100, description="Relative humidity percentage"
    )

    # Clouds and precipitation
    cloud_cover: CloudCover | None = Field(default=None, description="Cloud cover details")
    precipitation: Precipitation | None = Field(
        default=None, description="Precipitation details"
    )

    # Wind
    wind: Wind | None = Field(default=None, description="Wind details")

    # Pressure and visibility
    pressure_hpa: float | None = Field(
        default=None, description="Atmospheric pressure in hPa"
    )
    visibility_m: float | None = Field(
        default=None, ge=0, description="Visibility in meters"
    )

    # UV and air quality
    uv_index: float | None = Field(default=None, ge=0, description="UV index")

    # Astronomy (optional, may be populated for relevant forecasts)
    astronomical: AstronomicalData | None = Field(
        default=None, description="Astronomical data for this time"
    )

    # Provider-specific data
    raw_data: dict[str, Any] | None = Field(
        default=None, description="Raw data from weather provider"
    )

    @property
    def temperature_f(self) -> float:
        """Temperature in Fahrenheit."""
        return self.temperature_c * 9 / 5 + 32

    @property
    def feels_like_f(self) -> float | None:
        """Feels-like temperature in Fahrenheit."""
        return self.feels_like_c * 9 / 5 + 32 if self.feels_like_c else None

    @property
    def dew_point_f(self) -> float | None:
        """Dew point in Fahrenheit."""
        return self.dew_point_c * 9 / 5 + 32 if self.dew_point_c else None


class Forecast(BaseModel):
    """Complete weather forecast for a location."""

    location: Coordinates = Field(..., description="Location of the forecast")
    generated_at: datetime = Field(..., description="When the forecast was generated")
    provider: str = Field(..., description="Weather data provider name")

    hourly: list[HourlyForecast] = Field(
        default_factory=list, description="Hourly forecast data"
    )

    # Metadata
    timezone: str | None = Field(
        default=None, description="Timezone for the forecast location"
    )
    elevation_m: float | None = Field(
        default=None, description="Elevation in meters"
    )
    expires_at: datetime | None = Field(
        default=None, description="When this forecast data expires"
    )
    raw_response: dict[str, Any] | None = Field(
        default=None, description="Raw response from provider"
    )

    def get_forecast_at(self, time: datetime) -> HourlyForecast | None:
        """Get the forecast for a specific time (nearest hour)."""
        if not self.hourly:
            return None

        # Find the closest hourly forecast
        closest = min(
            self.hourly,
            key=lambda h: abs((h.time - time).total_seconds()),
        )

        # Only return if within 30 minutes
        if abs((closest.time - time).total_seconds()) <= 1800:
            return closest
        return None

    def get_forecast_range(
        self, start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        """Get all forecasts within a time range."""
        return [h for h in self.hourly if start <= h.time <= end]
