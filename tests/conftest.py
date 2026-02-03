"""Pytest fixtures for weather event recommendations tests."""

from datetime import datetime, timedelta, timezone

import pytest

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
