"""Pirate Weather provider.

## API Documentation Summary
Source: https://docs.pirateweather.net/en/latest/API/
Source: https://github.com/Pirate-Weather/pirateweather/blob/main/docs/API.md

## Overview
Pirate Weather is a free, open API that uses the Dark Sky API format.
It aggregates data from NOAA models (GFS, HRRR, NBM).

## Endpoint
- Base URL: https://api.pirateweather.net/forecast/{apikey}/{lat},{lon}
- Optional: Add Unix timestamp for historical/future: .../{lat},{lon},{time}
- Full URL example: https://api.pirateweather.net/forecast/YOUR_KEY/40.7128,-74.0060?units=si

## Authentication
- API key required (free tier available at https://pirate-weather.apiable.io/)
- Key is embedded in URL path, not header

## Rate Limiting
- Free tier: Limited requests/month (check API portal for current limits)
- Response headers include: X-RateLimit-Limit, X-RateLimit-Remaining

## Request Parameters
| Parameter | Description |
|-----------|-------------|
| units | si (default), us, ca, uk |
| exclude | Comma-separated: currently,minutely,hourly,daily,alerts |
| extend | hourly - extend to 168 hours instead of 48 |
| version | 2 for latest features |

## Response Format
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timezone": "America/New_York",
  "offset": -5,
  "elevation": 10.0,
  "currently": {
    "time": 1704067200,
    "summary": "Partly Cloudy",
    "icon": "partly-cloudy-day",
    "temperature": 5.2,
    "apparentTemperature": 2.1,
    ...
  },
  "hourly": {
    "summary": "Partly cloudy throughout the day.",
    "icon": "partly-cloudy-day",
    "data": [...]
  },
  "daily": {
    "summary": "Mixed conditions expected this week.",
    "icon": "partly-cloudy-day",
    "data": [...]
  },
  "alerts": []
}
```

## Variable Translation (PirateWeather SI units -> Canonical)

### Currently/Hourly Variables
| PirateWeather Field | Canonical Field | Unit (SI) | Notes |
|---------------------|-----------------|-----------|-------|
| time | time | Unix seconds | Convert to datetime |
| temperature | temperature_c | °C | Direct mapping |
| apparentTemperature | feels_like_c | °C | Direct mapping |
| dewPoint | dew_point_c | °C | Direct mapping |
| humidity | relative_humidity_percent | 0-1 | Multiply by 100 |
| pressure | pressure_hpa | hPa | Direct mapping |
| windSpeed | wind.speed_ms | m/s | Direct mapping |
| windGust | wind.gust_ms | m/s | Direct mapping |
| windBearing | wind.direction_deg | degrees | Direct mapping |
| cloudCover | cloud_cover.total_percent | 0-1 | Multiply by 100 |
| uvIndex | uv_index | index | Direct mapping |
| visibility | visibility_m | km | Multiply by 1000 |
| precipIntensity | precipitation.amount_mm | mm/h | Direct mapping |
| precipProbability | precipitation.probability_percent | 0-1 | Multiply by 100 |
| precipType | precipitation.type | string | Direct mapping |

### Icon -> WeatherCondition Mapping
| icon | WeatherCondition |
|------|------------------|
| clear-day, clear-night | CLEAR |
| partly-cloudy-day, partly-cloudy-night | PARTLY_CLOUDY |
| cloudy | CLOUDY |
| fog | FOG |
| wind | WINDY |
| rain | RAIN |
| sleet | SLEET |
| snow | SNOW |
| hail | HAIL |
| thunderstorm | THUNDERSTORM |

### Daily Variables (additional)
| PirateWeather Field | Canonical Field | Notes |
|---------------------|-----------------|-------|
| sunriseTime | astronomical.sunrise | Unix -> datetime |
| sunsetTime | astronomical.sunset | Unix -> datetime |
| moonPhase | astronomical.moon_phase | 0-1 |
| temperatureHigh | (daily high) | Not in hourly |
| temperatureLow | (daily low) | Not in hourly |
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from weather_events.models.location import Coordinates
from weather_events.models.weather import (
    AstronomicalData,
    CloudCover,
    Forecast,
    HourlyForecast,
    Precipitation,
    WeatherCondition,
    Wind,
)
from weather_events.providers.base import AuthenticationError, ProviderError, WeatherProvider


# Icon to WeatherCondition mapping
ICON_TO_CONDITION: dict[str, WeatherCondition] = {
    "clear-day": WeatherCondition.CLEAR,
    "clear-night": WeatherCondition.CLEAR,
    "partly-cloudy-day": WeatherCondition.PARTLY_CLOUDY,
    "partly-cloudy-night": WeatherCondition.PARTLY_CLOUDY,
    "cloudy": WeatherCondition.CLOUDY,
    "fog": WeatherCondition.FOG,
    "wind": WeatherCondition.WINDY,
    "rain": WeatherCondition.RAIN,
    "sleet": WeatherCondition.SLEET,
    "snow": WeatherCondition.SNOW,
    "hail": WeatherCondition.HAIL,
    "thunderstorm": WeatherCondition.THUNDERSTORM,
}


def _parse_icon(icon: str | None) -> WeatherCondition:
    """Parse PirateWeather icon to WeatherCondition."""
    if not icon:
        return WeatherCondition.UNKNOWN
    return ICON_TO_CONDITION.get(icon, WeatherCondition.UNKNOWN)


def _unix_to_datetime(timestamp: int | float | None) -> datetime | None:
    """Convert Unix timestamp to datetime."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


class PirateWeatherProvider(WeatherProvider):
    """Pirate Weather API provider.

    This provider fetches weather data from the Pirate Weather API, which
    provides Dark Sky-compatible data from NOAA models (GFS, HRRR, NBM).

    Example:
        ```python
        async with PirateWeatherProvider(api_key="your-api-key") as provider:
            forecast = await provider.get_forecast(
                Coordinates(latitude=40.7128, longitude=-74.0060)
            )
        ```
    """

    name = "pirateweather"
    base_url = "https://api.pirateweather.net/forecast"
    requires_api_key = True

    def __init__(
        self,
        api_key: str,
        user_agent: str | None = None,
        extend_hourly: bool = True,
        version: int = 2,
        timeout: float = 30.0,
    ):
        """Initialize Pirate Weather provider.

        Args:
            api_key: API key from pirate-weather.apiable.io
            user_agent: Optional User-Agent string
            extend_hourly: Extend hourly forecast to 168 hours (7 days)
            version: API version (2 recommended for latest features)
            timeout: Request timeout in seconds
        """
        super().__init__(api_key=api_key, user_agent=user_agent, timeout=timeout)
        self.extend_hourly = extend_hourly
        self.version = version

    async def get_forecast(
        self,
        coordinates: Coordinates,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Forecast:
        """Get weather forecast from Pirate Weather.

        Args:
            coordinates: Location (lat/lon)
            start_time: Optional start time (for time-machine requests)
            end_time: Not used

        Returns:
            Forecast in canonical format

        Raises:
            ProviderError: If request fails
            AuthenticationError: If API key is invalid
        """
        if not self.api_key:
            raise AuthenticationError(
                "API key required for Pirate Weather",
                provider=self.name,
            )

        # Build URL with coordinates
        coord_str = f"{coordinates.latitude},{coordinates.longitude}"
        if start_time:
            # Time-machine request for specific time
            unix_time = int(start_time.timestamp())
            coord_str = f"{coord_str},{unix_time}"

        url = f"{self.base_url}/{self.api_key}/{coord_str}"

        # Build query params
        params: dict[str, Any] = {
            "units": "si",  # Always request SI units
            "version": self.version,
        }
        if self.extend_hourly:
            params["extend"] = "hourly"

        response = await self._fetch(url, params=params)

        # Check for auth errors
        if response.status_code == 401:
            raise AuthenticationError(
                "Invalid API key",
                provider=self.name,
                status_code=401,
            )

        try:
            data = response.json()
        except Exception as e:
            raise ProviderError(
                f"Failed to parse response: {e}",
                provider=self.name,
                response_body=response.text,
            )

        return self._translate_response(data, coordinates)

    def _translate_response(
        self,
        response_data: dict[str, Any],
        coordinates: Coordinates,
    ) -> Forecast:
        """Translate Pirate Weather response to canonical format.

        See module docstring for detailed field mapping.
        """
        generated_at = datetime.now(timezone.utc)
        hourly: list[HourlyForecast] = []

        # Extract timezone
        tz_name = response_data.get("timezone")

        # Process hourly data
        hourly_block = response_data.get("hourly", {})
        hourly_data = hourly_block.get("data", [])

        # Also get daily data for astronomical info
        daily_block = response_data.get("daily", {})
        daily_data = daily_block.get("data", [])

        # Build a map of date -> astronomical data
        daily_astro: dict[str, AstronomicalData] = {}
        for day in daily_data:
            day_time = _unix_to_datetime(day.get("time"))
            if day_time:
                date_key = day_time.date().isoformat()
                daily_astro[date_key] = AstronomicalData(
                    sunrise=_unix_to_datetime(day.get("sunriseTime")),
                    sunset=_unix_to_datetime(day.get("sunsetTime")),
                    moon_phase=day.get("moonPhase"),
                )

        for hour_data in hourly_data:
            time = _unix_to_datetime(hour_data.get("time"))
            if not time:
                continue

            # Get temperature
            temp_c = hour_data.get("temperature")
            if temp_c is None:
                continue  # Skip entries without temperature

            # Build cloud cover (API returns 0-1, we need 0-100)
            cloud_cover = None
            cloud_fraction = hour_data.get("cloudCover")
            if cloud_fraction is not None:
                cloud_cover = CloudCover(total_percent=cloud_fraction * 100)

            # Build precipitation
            precipitation = None
            precip_prob = hour_data.get("precipProbability")
            precip_intensity = hour_data.get("precipIntensity")
            if precip_prob is not None or precip_intensity is not None:
                precipitation = Precipitation(
                    probability_percent=(precip_prob or 0) * 100,
                    amount_mm=precip_intensity,  # mm/h
                    type=hour_data.get("precipType"),
                )

            # Build wind
            wind = None
            wind_speed = hour_data.get("windSpeed")
            if wind_speed is not None:
                wind = Wind(
                    speed_ms=wind_speed,
                    gust_ms=hour_data.get("windGust"),
                    direction_deg=hour_data.get("windBearing"),
                )

            # Get astronomical data for this day
            date_key = time.date().isoformat()
            astro = daily_astro.get(date_key)

            # Determine weather condition
            icon = hour_data.get("icon")
            condition = _parse_icon(icon)

            # Visibility is in km for SI units, convert to meters
            visibility_km = hour_data.get("visibility")
            visibility_m = visibility_km * 1000 if visibility_km is not None else None

            hourly_forecast = HourlyForecast(
                time=time,
                condition=condition,
                temperature_c=temp_c,
                feels_like_c=hour_data.get("apparentTemperature"),
                dew_point_c=hour_data.get("dewPoint"),
                relative_humidity_percent=(
                    hour_data.get("humidity", 0) * 100
                    if hour_data.get("humidity") is not None
                    else None
                ),
                cloud_cover=cloud_cover,
                precipitation=precipitation,
                wind=wind,
                pressure_hpa=hour_data.get("pressure"),
                visibility_m=visibility_m,
                uv_index=hour_data.get("uvIndex"),
                astronomical=astro,
                raw_data=hour_data,
            )

            hourly.append(hourly_forecast)

        return Forecast(
            location=coordinates,
            generated_at=generated_at,
            provider=self.name,
            hourly=hourly,
            timezone=tz_name,
            elevation_m=response_data.get("elevation"),
            raw_response=response_data,
        )

    def supports_minute_forecast(self) -> bool:
        """Pirate Weather supports minute-by-minute precipitation."""
        return True

    def get_max_forecast_days(self) -> int:
        """Returns 7 days with extend=hourly, otherwise 2 days."""
        return 7 if self.extend_hourly else 2
