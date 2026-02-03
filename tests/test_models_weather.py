"""Tests for weather models."""

from datetime import datetime, timedelta, timezone

import pytest

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


class TestCloudCover:
    """Tests for CloudCover model."""

    def test_basic_cloud_cover(self):
        """Test creating basic cloud cover."""
        clouds = CloudCover(total_percent=50)
        assert clouds.total_percent == 50
        assert clouds.low_percent is None

    def test_detailed_cloud_cover(self):
        """Test cloud cover with all levels."""
        clouds = CloudCover(
            total_percent=70, low_percent=30, mid_percent=20, high_percent=20
        )
        assert clouds.total_percent == 70
        assert clouds.low_percent == 30

    def test_is_clear(self):
        """Test clear sky detection."""
        clear = CloudCover(total_percent=10)
        assert clear.is_clear() is True
        assert clear.is_clear(threshold=5) is False

        cloudy = CloudCover(total_percent=50)
        assert cloudy.is_clear() is False

    def test_is_mostly_clear(self):
        """Test mostly clear detection."""
        mostly_clear = CloudCover(total_percent=35)
        assert mostly_clear.is_mostly_clear() is True
        assert mostly_clear.is_clear() is False


class TestWind:
    """Tests for Wind model."""

    def test_basic_wind(self):
        """Test creating basic wind data."""
        wind = Wind(speed_ms=5.0)
        assert wind.speed_ms == 5.0
        assert wind.gust_ms is None

    def test_wind_with_gusts(self):
        """Test wind with gust data."""
        wind = Wind(speed_ms=5.0, gust_ms=8.0, direction_deg=180)
        assert wind.gust_ms == 8.0
        assert wind.direction_deg == 180

    def test_speed_conversions(self):
        """Test wind speed unit conversions."""
        wind = Wind(speed_ms=10.0)

        # 10 m/s should be about 22.37 mph
        assert wind.speed_mph == pytest.approx(22.37, rel=0.01)

        # 10 m/s should be 36 km/h
        assert wind.speed_kph == pytest.approx(36.0, rel=0.01)

    def test_gust_conversions(self):
        """Test gust speed conversions."""
        wind = Wind(speed_ms=5.0, gust_ms=10.0)
        assert wind.gust_mph == pytest.approx(22.37, rel=0.01)
        assert wind.gust_kph == pytest.approx(36.0, rel=0.01)

    def test_gust_conversions_none(self):
        """Test gust conversions when no gust data."""
        wind = Wind(speed_ms=5.0)
        assert wind.gust_mph is None
        assert wind.gust_kph is None

    def test_direction_cardinal(self):
        """Test wind direction cardinal conversion."""
        # North
        north = Wind(speed_ms=5.0, direction_deg=0)
        assert north.direction_cardinal() == "N"

        # East
        east = Wind(speed_ms=5.0, direction_deg=90)
        assert east.direction_cardinal() == "E"

        # South
        south = Wind(speed_ms=5.0, direction_deg=180)
        assert south.direction_cardinal() == "S"

        # West
        west = Wind(speed_ms=5.0, direction_deg=270)
        assert west.direction_cardinal() == "W"

        # Northeast
        ne = Wind(speed_ms=5.0, direction_deg=45)
        assert ne.direction_cardinal() == "NE"

    def test_direction_cardinal_none(self):
        """Test cardinal direction when no direction data."""
        wind = Wind(speed_ms=5.0)
        assert wind.direction_cardinal() is None


class TestPrecipitation:
    """Tests for Precipitation model."""

    def test_basic_precipitation(self):
        """Test creating basic precipitation data."""
        precip = Precipitation(probability_percent=30)
        assert precip.probability_percent == 30
        assert precip.amount_mm is None

    def test_precipitation_with_amount(self):
        """Test precipitation with amount."""
        precip = Precipitation(
            probability_percent=80, amount_mm=5.0, type="rain"
        )
        assert precip.amount_mm == 5.0
        assert precip.type == "rain"


class TestAstronomicalData:
    """Tests for AstronomicalData model."""

    def test_is_night(self):
        """Test night detection."""
        day = AstronomicalData(sun_altitude_deg=30)
        assert day.is_night() is False

        night = AstronomicalData(sun_altitude_deg=-10)
        assert night.is_night() is True

        # No data
        no_data = AstronomicalData()
        assert no_data.is_night() is None

    def test_is_astronomical_night(self):
        """Test astronomical night detection."""
        civil_twilight = AstronomicalData(sun_altitude_deg=-10)
        assert civil_twilight.is_astronomical_night() is False

        astro_night = AstronomicalData(sun_altitude_deg=-25)
        assert astro_night.is_astronomical_night() is True


class TestHourlyForecast:
    """Tests for HourlyForecast model."""

    def test_basic_forecast(self):
        """Test creating basic hourly forecast."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=22.0,
        )
        assert forecast.temperature_c == 22.0
        assert forecast.condition == WeatherCondition.UNKNOWN

    def test_temperature_conversion(self):
        """Test temperature unit conversion."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
            feels_like_c=18.0,
            dew_point_c=12.0,
        )

        # 20°C = 68°F
        assert forecast.temperature_f == pytest.approx(68.0)
        assert forecast.feels_like_f == pytest.approx(64.4)
        assert forecast.dew_point_f == pytest.approx(53.6)

    def test_feels_like_none(self):
        """Test feels-like when not provided."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
        )
        assert forecast.feels_like_f is None

    def test_complete_forecast(self, sample_hourly_forecast: HourlyForecast):
        """Test complete forecast with all fields."""
        f = sample_hourly_forecast
        assert f.temperature_c == 22.0
        assert f.cloud_cover is not None
        assert f.cloud_cover.total_percent == 40.0
        assert f.wind is not None
        assert f.wind.speed_ms == 3.5


class TestForecast:
    """Tests for Forecast model."""

    def test_basic_forecast(self, sample_coordinates: Coordinates):
        """Test creating basic forecast."""
        forecast = Forecast(
            location=sample_coordinates,
            generated_at=datetime.now(timezone.utc),
            provider="test",
        )
        assert forecast.provider == "test"
        assert len(forecast.hourly) == 0

    def test_get_forecast_at(self, sample_forecast: Forecast):
        """Test getting forecast at specific time."""
        # Get forecast at exact hour
        base = sample_forecast.hourly[0].time
        result = sample_forecast.get_forecast_at(base)
        assert result is not None
        assert result.time == base

        # Get forecast at time between hours (should return nearest)
        mid_time = base + timedelta(minutes=20)
        result = sample_forecast.get_forecast_at(mid_time)
        assert result is not None

    def test_get_forecast_at_none(self, sample_forecast: Forecast):
        """Test getting forecast at time outside range."""
        # Way before the forecast
        old_time = sample_forecast.hourly[0].time - timedelta(days=1)
        result = sample_forecast.get_forecast_at(old_time)
        assert result is None

    def test_get_forecast_range(self, sample_forecast: Forecast):
        """Test getting forecast for time range."""
        start = sample_forecast.hourly[0].time
        end = start + timedelta(hours=5)

        results = sample_forecast.get_forecast_range(start, end)
        assert len(results) == 6  # 6 hours inclusive
