"""MET Norway weather provider.

## API Documentation Summary
Source: https://api.met.no/weatherapi/locationforecast/2.0/documentation
Source: https://docs.api.met.no/doc/locationforecast/datamodel.html

## Endpoint
- Base URL: https://api.met.no/weatherapi/locationforecast/2.0/
- Formats: compact (default), complete
- Full URL example: https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=60.10&lon=9.58

## Authentication
- No API key required
- MUST include User-Agent header with application identifier
- Prohibited/missing User-Agent returns 403 Forbidden

## Rate Limiting
- No hard rate limit
- MUST implement caching using If-Modified-Since/Last-Modified headers
- Recommended: cache for at least 5 minutes between identical requests

## Response Format (GeoJSON)
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [longitude, latitude, altitude]
  },
  "properties": {
    "meta": {
      "updated_at": "2024-01-01T12:00:00Z",
      "units": {
        "air_temperature": "celsius",
        "wind_speed": "m/s",
        ...
      }
    },
    "timeseries": [
      {
        "time": "2024-01-01T12:00:00Z",
        "data": {
          "instant": {
            "details": {
              "air_temperature": 5.2,
              "wind_speed": 3.1,
              ...
            }
          },
          "next_1_hours": {
            "summary": {"symbol_code": "cloudy"},
            "details": {"precipitation_amount": 0.0}
          },
          "next_6_hours": {...},
          "next_12_hours": {...}
        }
      }
    ]
  }
}
```

## Variable Translation (MET.no -> Canonical)

### Instant Variables (properties.timeseries[].data.instant.details)
| MET.no Field | Canonical Field | Unit | Notes |
|--------------|-----------------|------|-------|
| air_temperature | temperature_c | °C | Direct mapping |
| air_pressure_at_sea_level | pressure_hpa | hPa | Direct mapping |
| cloud_area_fraction | cloud_cover.total_percent | % | Direct mapping |
| cloud_area_fraction_high | cloud_cover.high_percent | % | Complete only |
| cloud_area_fraction_medium | cloud_cover.mid_percent | % | Complete only |
| cloud_area_fraction_low | cloud_cover.low_percent | % | Complete only |
| dew_point_temperature | dew_point_c | °C | Direct mapping |
| fog_area_fraction | (custom) | % | Not in canonical |
| relative_humidity | relative_humidity_percent | % | Direct mapping |
| ultraviolet_index_clear_sky | uv_index | index | Direct mapping |
| wind_from_direction | wind.direction_deg | degrees | 0=N, 90=E |
| wind_speed | wind.speed_ms | m/s | Direct mapping |
| wind_speed_of_gust | wind.gust_ms | m/s | Complete only |

### Period Variables (next_1_hours, next_6_hours, next_12_hours)
| MET.no Field | Canonical Field | Unit | Notes |
|--------------|-----------------|------|-------|
| precipitation_amount | precipitation.amount_mm | mm | Accumulated |
| precipitation_amount_max | (not used) | mm | Complete only |
| precipitation_amount_min | (not used) | mm | Complete only |
| probability_of_precipitation | precipitation.probability_percent | % | Complete only |
| probability_of_thunder | (custom) | % | Not in canonical |

### Symbol Codes -> WeatherCondition
| symbol_code | WeatherCondition |
|-------------|------------------|
| clearsky_* | CLEAR |
| fair_* | PARTLY_CLOUDY |
| partlycloudy_* | PARTLY_CLOUDY |
| cloudy | CLOUDY |
| fog | FOG |
| lightrain* | LIGHT_RAIN |
| rain* | RAIN |
| heavyrain* | HEAVY_RAIN |
| lightrainshowers* | LIGHT_RAIN |
| rainshowers* | RAIN |
| heavyrainshowers* | HEAVY_RAIN |
| lightsnow* | LIGHT_SNOW |
| snow* | SNOW |
| heavysnow* | HEAVY_SNOW |
| sleet* | SLEET |
| thunder* | THUNDERSTORM |
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from weather_events.models.location import Coordinates
from weather_events.models.weather import (
    CloudCover,
    Forecast,
    HourlyForecast,
    Precipitation,
    WeatherCondition,
    Wind,
)
from weather_events.providers.base import ProviderError, WeatherProvider


# Symbol code to WeatherCondition mapping
SYMBOL_TO_CONDITION: dict[str, WeatherCondition] = {
    "clearsky": WeatherCondition.CLEAR,
    "fair": WeatherCondition.PARTLY_CLOUDY,
    "partlycloudy": WeatherCondition.PARTLY_CLOUDY,
    "cloudy": WeatherCondition.CLOUDY,
    "fog": WeatherCondition.FOG,
    "lightrain": WeatherCondition.LIGHT_RAIN,
    "lightrainshowers": WeatherCondition.LIGHT_RAIN,
    "rain": WeatherCondition.RAIN,
    "rainshowers": WeatherCondition.RAIN,
    "heavyrain": WeatherCondition.HEAVY_RAIN,
    "heavyrainshowers": WeatherCondition.HEAVY_RAIN,
    "lightsleet": WeatherCondition.SLEET,
    "sleet": WeatherCondition.SLEET,
    "heavysleet": WeatherCondition.SLEET,
    "lightsnow": WeatherCondition.LIGHT_SNOW,
    "lightsnowshowers": WeatherCondition.LIGHT_SNOW,
    "snow": WeatherCondition.SNOW,
    "snowshowers": WeatherCondition.SNOW,
    "heavysnow": WeatherCondition.HEAVY_SNOW,
    "heavysnowshowers": WeatherCondition.HEAVY_SNOW,
    "rainandthunder": WeatherCondition.THUNDERSTORM,
    "lightrainandthunder": WeatherCondition.THUNDERSTORM,
    "heavyrainandthunder": WeatherCondition.THUNDERSTORM,
    "snowandthunder": WeatherCondition.THUNDERSTORM,
}


def _parse_symbol_code(symbol_code: str | None) -> WeatherCondition:
    """Parse MET.no symbol code to WeatherCondition.

    Symbol codes may have suffixes like _day, _night, _polartwilight.
    We strip these suffixes for mapping.
    """
    if not symbol_code:
        return WeatherCondition.UNKNOWN

    # Remove time-of-day suffixes
    base_code = symbol_code.split("_")[0]

    return SYMBOL_TO_CONDITION.get(base_code, WeatherCondition.UNKNOWN)


class MetNoProvider(WeatherProvider):
    """MET Norway Locationforecast 2.0 provider.

    This provider fetches weather data from the Norwegian Meteorological
    Institute's free API. No API key is required, but a User-Agent header
    identifying your application is mandatory.

    Example:
        ```python
        async with MetNoProvider(user_agent="my-app/1.0 contact@example.com") as provider:
            forecast = await provider.get_forecast(
                Coordinates(latitude=59.9139, longitude=10.7522)
            )
        ```
    """

    name = "metno"
    base_url = "https://api.met.no/weatherapi/locationforecast/2.0"
    requires_api_key = False

    def __init__(
        self,
        user_agent: str | None = None,
        use_complete: bool = False,
        timeout: float = 30.0,
    ):
        """Initialize MET Norway provider.

        Args:
            user_agent: User-Agent string (REQUIRED by MET.no TOS).
                       Should include app name and contact info.
            use_complete: Use 'complete' endpoint for more variables
            timeout: Request timeout in seconds
        """
        super().__init__(user_agent=user_agent, timeout=timeout)
        self.use_complete = use_complete

    async def get_forecast(
        self,
        coordinates: Coordinates,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Forecast:
        """Get weather forecast from MET Norway.

        Args:
            coordinates: Location (lat/lon). Use max 4 decimal places.
            start_time: Not used (API returns full forecast)
            end_time: Not used (API returns full forecast)

        Returns:
            Forecast in canonical format

        Raises:
            ProviderError: If request fails
        """
        endpoint = "complete" if self.use_complete else "compact"
        url = f"{self.base_url}/{endpoint}"

        # MET.no requires max 4 decimal places
        params = {
            "lat": round(coordinates.latitude, 4),
            "lon": round(coordinates.longitude, 4),
        }

        response = await self._fetch(url, params=params)

        # Check for 304 Not Modified
        cache_key = f"{url}:{params}"
        if response.status_code == 304 and cache_key in self._response_cache:
            return self._response_cache[cache_key]

        try:
            data = response.json()
        except Exception as e:
            raise ProviderError(
                f"Failed to parse response: {e}",
                provider=self.name,
                response_body=response.text,
            )

        forecast = self._translate_response(data, coordinates)

        # Cache the response
        self._response_cache[cache_key] = forecast

        return forecast

    def _translate_response(
        self,
        response_data: dict[str, Any],
        coordinates: Coordinates,
    ) -> Forecast:
        """Translate MET.no response to canonical format.

        See module docstring for detailed field mapping.
        """
        properties = response_data.get("properties", {})
        meta = properties.get("meta", {})
        timeseries = properties.get("timeseries", [])

        # Parse generation time
        updated_at_str = meta.get("updated_at", "")
        try:
            generated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        except ValueError:
            generated_at = datetime.now(timezone.utc)

        # Parse hourly forecasts
        hourly: list[HourlyForecast] = []

        for entry in timeseries:
            time_str = entry.get("time", "")
            try:
                time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            data = entry.get("data", {})
            instant = data.get("instant", {}).get("details", {})

            # Get period data (prefer 1-hour, fall back to 6-hour)
            next_1h = data.get("next_1_hours", {})
            next_6h = data.get("next_6_hours", {})
            period_summary = next_1h.get("summary", next_6h.get("summary", {}))
            period_details = next_1h.get("details", next_6h.get("details", {}))

            # Build cloud cover
            cloud_cover = None
            total_cloud = instant.get("cloud_area_fraction")
            if total_cloud is not None:
                cloud_cover = CloudCover(
                    total_percent=total_cloud,
                    low_percent=instant.get("cloud_area_fraction_low"),
                    mid_percent=instant.get("cloud_area_fraction_medium"),
                    high_percent=instant.get("cloud_area_fraction_high"),
                )

            # Build precipitation
            precipitation = None
            precip_amount = period_details.get("precipitation_amount")
            precip_prob = period_details.get("probability_of_precipitation")
            if precip_amount is not None or precip_prob is not None:
                precipitation = Precipitation(
                    probability_percent=precip_prob if precip_prob is not None else 0,
                    amount_mm=precip_amount,
                )

            # Build wind
            wind = None
            wind_speed = instant.get("wind_speed")
            if wind_speed is not None:
                wind = Wind(
                    speed_ms=wind_speed,
                    gust_ms=instant.get("wind_speed_of_gust"),
                    direction_deg=instant.get("wind_from_direction"),
                )

            # Determine weather condition from symbol
            symbol_code = period_summary.get("symbol_code")
            condition = _parse_symbol_code(symbol_code)

            hourly_forecast = HourlyForecast(
                time=time,
                condition=condition,
                temperature_c=instant.get("air_temperature", 0),
                feels_like_c=None,  # MET.no doesn't provide feels-like directly
                dew_point_c=instant.get("dew_point_temperature"),
                relative_humidity_percent=instant.get("relative_humidity"),
                cloud_cover=cloud_cover,
                precipitation=precipitation,
                wind=wind,
                pressure_hpa=instant.get("air_pressure_at_sea_level"),
                uv_index=instant.get("ultraviolet_index_clear_sky"),
                raw_data=entry,
            )

            hourly.append(hourly_forecast)

        return Forecast(
            location=coordinates,
            generated_at=generated_at,
            provider=self.name,
            hourly=hourly,
            raw_response=response_data,
        )

    def get_max_forecast_days(self) -> int:
        """MET.no provides up to 9 days of forecast."""
        return 9
