"""Pytest fixtures for weather event recommendations tests.

This module provides test fixtures that ensure:
1. No external API calls are made (weather providers, Google APIs)
2. No real database connections in unit tests
3. Isolated test environment with controlled configuration
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment BEFORE importing application modules
# This ensures no real services are contacted during test collection
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

from weather_events.models.location import Coordinates, Location
from weather_events.models.weather import (
    AstronomicalData,
    CloudCover,
    Forecast,
    HourlyForecast,
    Precipitation,
    WeatherCondition,
    Wind,
)
from weather_events.models.activity import (
    Activity,
    ActivityCategory,
    ActivityRequirements,
    CloudConstraints,
    PrecipitationConstraints,
    SunConstraints,
    TemperatureRange,
    WindConstraints,
)


# =============================================================================
# Test Isolation Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset settings cache before each test to ensure clean state."""
    from weather_events.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_weather_provider():
    """Mock weather provider to prevent external API calls."""
    with patch("weather_events.providers.metno.MetNoProvider") as mock_metno, \
         patch("weather_events.providers.pirateweather.PirateWeatherProvider") as mock_pirate:

        # Configure mock responses
        mock_forecast = Forecast(
            location=Coordinates(latitude=40.7128, longitude=-74.0060),
            generated_at=datetime.now(timezone.utc),
            provider="mock",
            hourly=[
                HourlyForecast(
                    time=datetime.now(timezone.utc) + timedelta(hours=i),
                    temperature_c=20.0,
                    condition=WeatherCondition.CLEAR,
                )
                for i in range(24)
            ],
        )

        mock_metno.return_value.get_forecast = AsyncMock(return_value=mock_forecast)
        mock_pirate.return_value.get_forecast = AsyncMock(return_value=mock_forecast)

        yield {"metno": mock_metno, "pirateweather": mock_pirate}


@pytest.fixture
def mock_google_oauth():
    """Mock Google OAuth to prevent external authentication calls."""
    with patch("weather_events.auth.google.GoogleOAuth") as mock_oauth:
        mock_instance = MagicMock()
        mock_instance.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?test=1",
            "test-state-token"
        )
        mock_instance.exchange_code = AsyncMock(return_value={
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        })
        mock_instance.get_user_info = AsyncMock(return_value={
            "id": "test-google-id",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        })
        mock_instance.refresh_token = AsyncMock(return_value={
            "access_token": "refreshed-access-token",
            "expires_in": 3600,
        })
        mock_oauth.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_google_calendar():
    """Mock Google Calendar API to prevent external calls."""
    with patch("weather_events.calendar.google_calendar.GoogleCalendarClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.list_calendars = AsyncMock(return_value=[
            {
                "id": "primary",
                "summary": "Primary Calendar",
                "primary": True,
            },
            {
                "id": "test-calendar-id",
                "summary": "Test Calendar",
                "primary": False,
            },
        ])
        mock_instance.list_events = AsyncMock(return_value=[])
        mock_instance.update_event = AsyncMock(return_value={
            "id": "test-event-id",
            "summary": "Updated Event",
        })
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client to prevent any external HTTP calls."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock()
        mock_instance.post = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_coordinates() -> Coordinates:
    """Sample coordinates for New York City."""
    return Coordinates(latitude=40.7128, longitude=-74.0060)


@pytest.fixture
def sample_location(sample_coordinates: Coordinates) -> Location:
    """Sample location with coordinates and timezone."""
    return Location(
        coordinates=sample_coordinates,
        timezone="America/New_York",
        name="New York City",
    )


@pytest.fixture
def sample_hourly_forecast() -> HourlyForecast:
    """Sample hourly forecast with typical mild conditions."""
    return HourlyForecast(
        time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
        condition=WeatherCondition.PARTLY_CLOUDY,
        temperature_c=22.0,
        feels_like_c=23.0,
        dew_point_c=15.0,
        relative_humidity_percent=60.0,
        cloud_cover=CloudCover(total_percent=40.0),
        precipitation=Precipitation(probability_percent=10.0, amount_mm=0.0),
        wind=Wind(speed_ms=3.5, gust_ms=5.0, direction_deg=180),
        pressure_hpa=1015.0,
        visibility_m=10000.0,
        uv_index=6.0,
    )


@pytest.fixture
def cold_forecast() -> HourlyForecast:
    """Sample hourly forecast with cold conditions."""
    return HourlyForecast(
        time=datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc),
        condition=WeatherCondition.CLEAR,
        temperature_c=-5.0,
        feels_like_c=-10.0,
        dew_point_c=-12.0,
        relative_humidity_percent=70.0,
        cloud_cover=CloudCover(total_percent=5.0),
        precipitation=Precipitation(probability_percent=0.0),
        wind=Wind(speed_ms=5.0, gust_ms=8.0, direction_deg=315),
        pressure_hpa=1025.0,
        visibility_m=20000.0,
    )


@pytest.fixture
def rainy_forecast() -> HourlyForecast:
    """Sample hourly forecast with rainy conditions."""
    return HourlyForecast(
        time=datetime(2024, 4, 15, 14, 0, tzinfo=timezone.utc),
        condition=WeatherCondition.RAIN,
        temperature_c=15.0,
        feels_like_c=14.0,
        relative_humidity_percent=85.0,
        cloud_cover=CloudCover(total_percent=90.0),
        precipitation=Precipitation(probability_percent=80.0, amount_mm=5.0),
        wind=Wind(speed_ms=6.0, gust_ms=10.0, direction_deg=225),
        pressure_hpa=1005.0,
        visibility_m=5000.0,
    )


@pytest.fixture
def clear_night_forecast() -> HourlyForecast:
    """Sample hourly forecast for clear night (astronomy)."""
    return HourlyForecast(
        time=datetime(2024, 6, 15, 23, 0, tzinfo=timezone.utc),
        condition=WeatherCondition.CLEAR,
        temperature_c=18.0,
        feels_like_c=17.0,
        relative_humidity_percent=55.0,
        cloud_cover=CloudCover(total_percent=5.0, high_percent=3.0),
        precipitation=Precipitation(probability_percent=0.0),
        wind=Wind(speed_ms=2.0, gust_ms=3.0, direction_deg=90),
        pressure_hpa=1018.0,
        visibility_m=30000.0,
        astronomical=AstronomicalData(
            sun_altitude_deg=-25.0,  # Below -18°, astronomical night
            moon_illumination_percent=15.0,
            moon_altitude_deg=-10.0,
        ),
    )


@pytest.fixture
def sample_forecast(sample_coordinates: Coordinates) -> Forecast:
    """Sample complete forecast with multiple hours."""
    base_time = datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc)
    hourly = []

    for i in range(24):
        time = base_time + timedelta(hours=i)

        # Vary conditions through the day
        if 6 <= i <= 8:
            temp = 18 + i - 6
            clouds = 20
            condition = WeatherCondition.CLEAR
        elif 9 <= i <= 16:
            temp = 22 + (i - 9) * 0.5
            clouds = 30 + (i - 9) * 5
            condition = WeatherCondition.PARTLY_CLOUDY
        else:
            temp = 20 - abs(i - 12) * 0.3
            clouds = 20
            condition = WeatherCondition.CLEAR

        hourly.append(
            HourlyForecast(
                time=time,
                condition=condition,
                temperature_c=temp,
                feels_like_c=temp - 1,
                cloud_cover=CloudCover(total_percent=clouds),
                precipitation=Precipitation(probability_percent=5.0),
                wind=Wind(speed_ms=3.0 + i * 0.1),
            )
        )

    return Forecast(
        location=sample_coordinates,
        generated_at=datetime.now(timezone.utc),
        provider="test",
        hourly=hourly,
    )


@pytest.fixture
def running_activity() -> Activity:
    """Sample running activity with typical requirements."""
    return Activity(
        id="running_test",
        name="Running",
        category=ActivityCategory.EXERCISE,
        requirements=ActivityRequirements(
            temperature=TemperatureRange(
                min_c=-10,
                max_c=35,
                ideal_min_c=10,
                ideal_max_c=22,
            ),
            wind=WindConstraints(
                max_speed_ms=12,
                ideal_max_speed_ms=6,
            ),
            precipitation=PrecipitationConstraints(
                max_probability_percent=50,
                allow_light_rain=True,
            ),
        ),
    )


@pytest.fixture
def astronomy_activity() -> Activity:
    """Sample astronomy activity with requirements."""
    return Activity(
        id="astronomy_test",
        name="Astronomy Observing",
        category=ActivityCategory.ASTRONOMY,
        requirements=ActivityRequirements(
            temperature=TemperatureRange(min_c=-15),
            wind=WindConstraints(max_speed_ms=8, max_gust_ms=12),
            clouds=CloudConstraints(max_total_percent=30, ideal_max_total_percent=10),
            precipitation=PrecipitationConstraints(max_probability_percent=10),
            sun=SunConstraints(require_below_horizon=True),
        ),
    )


@pytest.fixture
def solar_observation_activity() -> Activity:
    """Sample solar observation activity."""
    return Activity(
        id="solar_test",
        name="Solar Observation",
        category=ActivityCategory.ASTRONOMY,
        requirements=ActivityRequirements(
            wind=WindConstraints(max_speed_ms=5),
            clouds=CloudConstraints(max_total_percent=15),
            sun=SunConstraints(min_altitude_deg=20),
        ),
    )
