"""Tests for weather models."""

from datetime import datetime, timedelta, timezone

import pytest

from weather_events.models.location import Coordinates
from weather_events.models.weather import (
    AstronomicalData,
    CloudCover,
    ConditionFlags,
    Forecast,
    HourlyForecast,
    Precipitation,
    SunEffectConfig,
    TimeOfDay,
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


class TestConditionFlags:
    """Tests for ConditionFlags parsing."""

    def test_from_condition_clear(self):
        """Test flags for clear condition."""
        flags = ConditionFlags.from_condition(WeatherCondition.CLEAR)
        assert not flags.is_rain
        assert not flags.is_snow
        assert not flags.is_cloudy
        assert not flags.is_thunderstorm

    def test_from_condition_rain(self):
        """Test flags for rain conditions."""
        flags = ConditionFlags.from_condition(WeatherCondition.RAIN)
        assert flags.is_rain
        assert not flags.is_light
        assert not flags.is_heavy

        light = ConditionFlags.from_condition(WeatherCondition.LIGHT_RAIN)
        assert light.is_rain
        assert light.is_light

        heavy = ConditionFlags.from_condition(WeatherCondition.HEAVY_RAIN)
        assert heavy.is_rain
        assert heavy.is_heavy

    def test_from_condition_snow(self):
        """Test flags for snow conditions."""
        flags = ConditionFlags.from_condition(WeatherCondition.SNOW)
        assert flags.is_snow
        assert not flags.is_rain

    def test_from_condition_thunderstorm(self):
        """Test flags for thunderstorm."""
        flags = ConditionFlags.from_condition(WeatherCondition.THUNDERSTORM)
        assert flags.is_thunderstorm
        assert not flags.is_rain  # Thunderstorm is separate

    def test_from_description(self):
        """Test parsing from text description."""
        flags = ConditionFlags.from_description("Chance of Light Rain")
        assert flags.is_rain
        assert flags.is_chance
        assert flags.is_light

        flags2 = ConditionFlags.from_description("Heavy Thunderstorms")
        assert flags2.is_thunderstorm
        assert flags2.is_heavy

    def test_is_wet(self):
        """Test wet condition detection."""
        rain = ConditionFlags.from_condition(WeatherCondition.RAIN)
        assert rain.is_wet()

        clear = ConditionFlags.from_condition(WeatherCondition.CLEAR)
        assert not clear.is_wet()


class TestSunEffectConfig:
    """Tests for sun effect configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SunEffectConfig()
        assert config.min_altitude_zero_effect == 10.0
        assert config.min_altitude_full_effect == 45.0
        assert config.min_effect_when_visible == 0.0

    def test_sun_factor_below_zero(self):
        """Test sun factor when below zero-effect threshold."""
        config = SunEffectConfig(min_altitude_zero_effect=10, min_altitude_full_effect=45)
        assert config.calculate_sun_factor(5) == 0.0
        assert config.calculate_sun_factor(0) == 0.0
        assert config.calculate_sun_factor(-10) == 0.0

    def test_sun_factor_above_full(self):
        """Test sun factor when above full-effect threshold."""
        config = SunEffectConfig(min_altitude_zero_effect=10, min_altitude_full_effect=45)
        assert config.calculate_sun_factor(45) == 1.0
        assert config.calculate_sun_factor(60) == 1.0
        assert config.calculate_sun_factor(90) == 1.0

    def test_sun_factor_interpolation(self):
        """Test linear interpolation between thresholds."""
        config = SunEffectConfig(min_altitude_zero_effect=10, min_altitude_full_effect=45)

        # Midpoint should be 0.5
        midpoint = (10 + 45) / 2  # 27.5
        assert config.calculate_sun_factor(midpoint) == pytest.approx(0.5)

        # Quarter point
        quarter = 10 + (45 - 10) * 0.25  # 18.75
        assert config.calculate_sun_factor(quarter) == pytest.approx(0.25)

    def test_sun_factor_none(self):
        """Test sun factor with no altitude data (backward compatible)."""
        config = SunEffectConfig()
        assert config.calculate_sun_factor(None) == 1.0


class TestRelativeTemperature:
    """Tests for relative temperature calculation."""

    def test_basic_relative_temp(self):
        """Test basic relative temperature (no adjustments)."""
        # Clear day, no wind - should get full sun effect
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,  # 68°F
            condition=WeatherCondition.CLEAR,
            astronomical=AstronomicalData(
                sun_altitude_deg=60,
                sunrise=datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                sunset=datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc),
            ),
        )
        # 68°F + 10°F (clear day) = 78°F
        relative = forecast.get_relative_temperature_f()
        assert relative == pytest.approx(78.0)

    def test_relative_temp_wind_adjustment(self):
        """Test wind reduces relative temperature."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,  # 68°F
            condition=WeatherCondition.CLEAR,
            wind=Wind(speed_ms=4.47),  # ~10 mph
            astronomical=AstronomicalData(
                sun_altitude_deg=60,
                sunrise=datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                sunset=datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc),
            ),
        )
        # 68°F - 9°F (wind, max) + 10°F (sun) = 69°F
        relative = forecast.get_relative_temperature_f()
        # Wind is ~10 mph, capped at 9°F reduction
        assert relative < 78.0  # Less than no-wind case

    def test_relative_temp_rain_adjustment(self):
        """Test rain reduces relative temperature."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,  # 68°F
            condition=WeatherCondition.RAIN,
            astronomical=AstronomicalData(
                sun_altitude_deg=60,
                sunrise=datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                sunset=datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc),
            ),
        )
        # 68°F - 7°F (rain) + 0°F (wet=no sun effect) = 61°F
        relative = forecast.get_relative_temperature_f()
        assert relative == pytest.approx(61.0)

    def test_relative_temp_low_sun(self):
        """Test low sun altitude reduces warming effect."""
        # High sun
        high_sun = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
            condition=WeatherCondition.CLEAR,
            astronomical=AstronomicalData(
                sun_altitude_deg=60,
                sunrise=datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                sunset=datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc),
            ),
        )

        # Low sun (winter-like)
        low_sun = HourlyForecast(
            time=datetime(2024, 12, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
            condition=WeatherCondition.CLEAR,
            astronomical=AstronomicalData(
                sun_altitude_deg=20,  # Low winter sun
                sunrise=datetime(2024, 12, 15, 7, 0, tzinfo=timezone.utc),
                sunset=datetime(2024, 12, 15, 17, 0, tzinfo=timezone.utc),
            ),
        )

        high_relative = high_sun.get_relative_temperature_f()
        low_relative = low_sun.get_relative_temperature_f()

        # Low sun should have less warming effect
        assert low_relative < high_relative

    def test_relative_temp_custom_sun_config(self):
        """Test relative temperature with custom sun configuration."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,  # 68°F
            condition=WeatherCondition.CLEAR,
            astronomical=AstronomicalData(
                sun_altitude_deg=15,  # Low angle
                sunrise=datetime(2024, 6, 15, 6, 0, tzinfo=timezone.utc),
                sunset=datetime(2024, 6, 15, 20, 0, tzinfo=timezone.utc),
            ),
        )

        # Wooded trail config - needs higher altitude for effect
        wooded_config = SunEffectConfig(
            min_altitude_zero_effect=20,  # Trees block until 20°
            min_altitude_full_effect=50,
        )

        # With default config at 15°, some sun effect
        default_temp = forecast.get_relative_temperature_f()

        # With wooded config, sun below tree line = no effect
        wooded_temp = forecast.get_relative_temperature_f(sun_config=wooded_config)

        assert wooded_temp < default_temp
        assert wooded_temp == 68.0  # Just base temp, no sun effect
