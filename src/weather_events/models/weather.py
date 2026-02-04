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


class TimeOfDay(str, Enum):
    """Time of day classification for relative temperature adjustments.

    Used to adjust perceived temperature based on sun exposure.
    Dawn/dusk are transitional periods with partial sun effect.
    """

    NIGHT = "night"  # Sun well below horizon, no warming effect
    DAWN = "dawn"  # Approaching sunrise, slight warming
    DAY = "day"  # Sun above horizon, full warming effect
    DUSK = "dusk"  # After sunset, diminishing warmth


class ConditionFlags(BaseModel):
    """Parsed weather condition flags.

    Used for clothing rules and relative temperature calculation.
    Matches legacy system's condition parsing for consistency.
    """

    is_rain: bool = False
    is_snow: bool = False
    is_cloudy: bool = False
    is_thunderstorm: bool = False
    is_slight: bool = False  # "slight chance"
    is_chance: bool = False  # "chance of" / "likely" / "isolated"
    is_light: bool = False  # "light" / "partial" / "patches"
    is_heavy: bool = False  # "heavy"

    @classmethod
    def from_condition(cls, condition: WeatherCondition) -> "ConditionFlags":
        """Create flags from a WeatherCondition enum."""
        flags = cls()

        if condition == WeatherCondition.THUNDERSTORM:
            flags.is_thunderstorm = True
        elif condition in (
            WeatherCondition.SNOW,
            WeatherCondition.HEAVY_SNOW,
            WeatherCondition.LIGHT_SNOW,
            WeatherCondition.SLEET,
            WeatherCondition.HAIL,
        ):
            flags.is_snow = True
            if condition == WeatherCondition.HEAVY_SNOW:
                flags.is_heavy = True
            elif condition == WeatherCondition.LIGHT_SNOW:
                flags.is_light = True
        elif condition in (
            WeatherCondition.RAIN,
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.LIGHT_RAIN,
            WeatherCondition.DRIZZLE,
        ):
            flags.is_rain = True
            if condition == WeatherCondition.HEAVY_RAIN:
                flags.is_heavy = True
            elif condition in (WeatherCondition.LIGHT_RAIN, WeatherCondition.DRIZZLE):
                flags.is_light = True
        elif condition in (
            WeatherCondition.CLOUDY,
            WeatherCondition.OVERCAST,
            WeatherCondition.FOG,
            WeatherCondition.PARTLY_CLOUDY,
        ):
            flags.is_cloudy = True
            if condition == WeatherCondition.PARTLY_CLOUDY:
                flags.is_light = True

        return flags

    @classmethod
    def from_description(cls, description: str) -> "ConditionFlags":
        """Parse condition flags from a text description.

        Handles descriptions like "Chance of Light Rain" or "Partly Cloudy".
        """
        flags = cls()
        desc_upper = description.upper()

        # Parse modifiers
        flags.is_slight = "SLIGHT CHANCE" in desc_upper
        flags.is_chance = any(
            x in desc_upper for x in ["CHANCE", "LIKELY", "ISOLATED"]
        )
        flags.is_light = any(
            x in desc_upper for x in ["LIGHT", "PARTIAL", "PATCHES", "SHALLOW"]
        )
        flags.is_heavy = "HEAVY" in desc_upper

        # Parse condition (order matters - worst first)
        if "THUNDERSTORM" in desc_upper:
            flags.is_thunderstorm = True
        elif any(x in desc_upper for x in ["SNOW", "HAIL", "ICE", "SLEET"]):
            flags.is_snow = True
        elif "SQUALLS" in desc_upper:
            flags.is_rain = True
            flags.is_light = False
            flags.is_heavy = True
        elif any(x in desc_upper for x in ["RAIN", "SHOWERS"]):
            flags.is_rain = True
        elif "DRIZZLE" in desc_upper:
            flags.is_rain = True
            flags.is_light = True
        elif any(x in desc_upper for x in ["FOG", "HAZE", "MIST"]):
            flags.is_cloudy = True
        elif "OVERCAST" in desc_upper:
            flags.is_cloudy = True
        elif any(x in desc_upper for x in ["CLOUDY", "CLOUDS"]):
            flags.is_cloudy = True

        return flags

    def is_wet(self) -> bool:
        """Check if conditions involve wetness (affects relative temp)."""
        return self.is_rain or self.is_thunderstorm or self.is_snow


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

    def get_time_of_day(
        self,
        dawn_minutes: int = 30,
        dusk_minutes: int = 30,
    ) -> TimeOfDay:
        """Determine time of day classification.

        Args:
            dawn_minutes: Minutes before sunrise to consider as dawn
            dusk_minutes: Minutes after sunset to consider as dusk

        Returns:
            TimeOfDay classification
        """
        if not self.astronomical:
            # Default to day if no astronomical data
            return TimeOfDay.DAY

        sunrise = self.astronomical.sunrise
        sunset = self.astronomical.sunset

        if not sunrise or not sunset:
            # Fall back to sun altitude if available
            if self.astronomical.sun_altitude_deg is not None:
                if self.astronomical.sun_altitude_deg < -6:
                    return TimeOfDay.NIGHT
                elif self.astronomical.sun_altitude_deg < 0:
                    return TimeOfDay.DUSK  # or DAWN, hard to tell without times
                else:
                    return TimeOfDay.DAY
            return TimeOfDay.DAY

        from datetime import timedelta

        dawn_start = sunrise - timedelta(minutes=dawn_minutes)
        dusk_end = sunset + timedelta(minutes=dusk_minutes)

        if self.time < dawn_start:
            return TimeOfDay.NIGHT
        elif self.time < sunrise:
            return TimeOfDay.DAWN
        elif self.time < sunset:
            return TimeOfDay.DAY
        elif self.time < dusk_end:
            return TimeOfDay.DUSK
        else:
            return TimeOfDay.NIGHT

    def get_condition_flags(self) -> ConditionFlags:
        """Get parsed condition flags for this forecast."""
        return ConditionFlags.from_condition(self.condition)

    def get_relative_temperature_f(
        self,
        time_of_day: TimeOfDay | None = None,
    ) -> float:
        """Calculate relative/perceived temperature in Fahrenheit.

        This is a custom calculation that adjusts actual temperature for:
        - Precipitation effect (getting wet makes you colder)
        - Wind chill (each mph reduces perceived temp)
        - Sun exposure (being in sun during day warms you up)

        This differs from "feels like" which only accounts for wind chill
        and humidity. Relative temperature is more useful for activity planning.

        Args:
            time_of_day: Override time of day (auto-detected if None)

        Returns:
            Relative temperature in Fahrenheit
        """
        temp_f = self.temperature_f
        conditions = self.get_condition_flags()
        tod = time_of_day or self.get_time_of_day()
        wind_mph = self.wind.speed_mph if self.wind else 0

        # Start with actual temperature
        relative_temp_f = temp_f

        # Precipitation adjustments (getting wet makes you feel colder)
        if not conditions.is_slight:
            if conditions.is_thunderstorm:
                if conditions.is_chance:
                    relative_temp_f -= 4
                else:
                    relative_temp_f -= 10  # Same as heavy rain
            elif conditions.is_rain:
                if conditions.is_chance:
                    relative_temp_f -= 3
                elif conditions.is_light:
                    relative_temp_f -= 4
                elif conditions.is_heavy:
                    relative_temp_f -= 10
                else:
                    relative_temp_f -= 7
            elif conditions.is_snow:
                relative_temp_f -= 3

        # Wind adjustment: -1°F per mph, max -9°F
        relative_temp_f -= min(9, wind_mph)

        # Sun exposure adjustment (only if not wet)
        if not conditions.is_wet():
            if tod == TimeOfDay.DAY:
                if conditions.is_cloudy:
                    if conditions.is_light:  # partly cloudy
                        relative_temp_f += 5
                    else:  # overcast
                        relative_temp_f += 2
                else:  # clear
                    relative_temp_f += 10
            elif tod in (TimeOfDay.DAWN, TimeOfDay.DUSK):
                if conditions.is_cloudy and conditions.is_light:
                    relative_temp_f += 2
                elif not conditions.is_cloudy:  # clear
                    relative_temp_f += 5
            # Night: no sun adjustment

        return relative_temp_f

    def get_relative_temperature_c(
        self,
        time_of_day: TimeOfDay | None = None,
    ) -> float:
        """Calculate relative/perceived temperature in Celsius.

        See get_relative_temperature_f for details.
        """
        return (self.get_relative_temperature_f(time_of_day) - 32) * 5 / 9


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
