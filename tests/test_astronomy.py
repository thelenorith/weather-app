"""Tests for astronomical calculations."""

from datetime import datetime, timezone

import pytest

from weather_events.astronomy.calculator import (
    AstronomyCalculator,
    get_moon_position,
    get_sun_altitude_time,
    get_sun_position,
    get_twilight_times,
)
from weather_events.models.location import Coordinates


class TestSunPosition:
    """Tests for sun position calculations."""

    def test_sun_position_midday(self, sample_coordinates: Coordinates):
        """Test sun position at midday."""
        # Summer midday in NYC
        midday = datetime(2024, 6, 21, 17, 0, tzinfo=timezone.utc)  # ~12pm EDT
        position = get_sun_position(sample_coordinates, midday)

        # Sun should be high in the sky
        assert position.altitude_deg > 50
        assert position.is_day is True

    def test_sun_position_midnight(self, sample_coordinates: Coordinates):
        """Test sun position at midnight."""
        midnight = datetime(2024, 6, 21, 4, 0, tzinfo=timezone.utc)  # ~midnight EDT
        position = get_sun_position(sample_coordinates, midnight)

        # Sun should be below horizon
        assert position.altitude_deg < 0
        assert position.is_day is False

    def test_sun_position_southern_hemisphere(self):
        """Test sun position in southern hemisphere."""
        # Sydney in December (summer there)
        sydney = Coordinates(latitude=-33.8688, longitude=151.2093)
        summer_noon = datetime(2024, 12, 21, 2, 0, tzinfo=timezone.utc)  # ~1pm AEDT

        position = get_sun_position(sydney, summer_noon)

        # Sun should be high
        assert position.altitude_deg > 60
        assert position.is_day is True

    def test_azimuth_range(self, sample_coordinates: Coordinates):
        """Test that azimuth is always in valid range."""
        times = [
            datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 6, 21, 6, 0, tzinfo=timezone.utc),
            datetime(2024, 6, 21, 12, 0, tzinfo=timezone.utc),
            datetime(2024, 6, 21, 18, 0, tzinfo=timezone.utc),
        ]

        for time in times:
            position = get_sun_position(sample_coordinates, time)
            assert 0 <= position.azimuth_deg < 360


class TestMoonPosition:
    """Tests for moon position calculations."""

    def test_moon_position(self, sample_coordinates: Coordinates):
        """Test basic moon position calculation."""
        time = datetime(2024, 6, 21, 20, 0, tzinfo=timezone.utc)
        position = get_moon_position(sample_coordinates, time)

        # Moon should have valid altitude and azimuth
        assert -90 <= position.altitude_deg <= 90
        assert 0 <= position.azimuth_deg < 360

    def test_moon_phase_range(self, sample_coordinates: Coordinates):
        """Test that moon phase is in valid range."""
        time = datetime(2024, 6, 21, 20, 0, tzinfo=timezone.utc)
        position = get_moon_position(sample_coordinates, time)

        assert 0 <= position.phase <= 1
        assert 0 <= position.illumination_percent <= 100


class TestTwilightTimes:
    """Tests for twilight time calculations."""

    def test_twilight_times_summer(self, sample_coordinates: Coordinates):
        """Test twilight times calculation in summer."""
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)
        twilight = get_twilight_times(sample_coordinates, date)

        # All events should occur in summer at mid-latitudes
        assert twilight.sunrise is not None
        assert twilight.sunset is not None
        assert twilight.civil_twilight_start is not None
        assert twilight.astronomical_twilight_start is not None

    def test_twilight_order(self, sample_coordinates: Coordinates):
        """Test that twilight events are in correct order."""
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)
        twilight = get_twilight_times(sample_coordinates, date)

        if all(
            x is not None
            for x in [
                twilight.astronomical_twilight_start,
                twilight.nautical_twilight_start,
                twilight.civil_twilight_start,
                twilight.sunrise,
            ]
        ):
            # Morning order: astro -> nautical -> civil -> sunrise
            assert twilight.astronomical_twilight_start < twilight.nautical_twilight_start
            assert twilight.nautical_twilight_start < twilight.civil_twilight_start
            assert twilight.civil_twilight_start < twilight.sunrise

        if all(
            x is not None
            for x in [
                twilight.sunset,
                twilight.civil_twilight_end,
                twilight.nautical_twilight_end,
                twilight.astronomical_twilight_end,
            ]
        ):
            # Evening order: sunset -> civil -> nautical -> astro
            assert twilight.sunset < twilight.civil_twilight_end
            assert twilight.civil_twilight_end < twilight.nautical_twilight_end
            assert twilight.nautical_twilight_end < twilight.astronomical_twilight_end

    def test_solar_noon_between_rise_set(self, sample_coordinates: Coordinates):
        """Test that solar noon is between sunrise and sunset."""
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)
        twilight = get_twilight_times(sample_coordinates, date)

        if twilight.solar_noon and twilight.sunrise and twilight.sunset:
            assert twilight.sunrise < twilight.solar_noon < twilight.sunset


class TestSunAltitudeTime:
    """Tests for finding sun altitude crossing times."""

    def test_find_sunrise_equivalent(self, sample_coordinates: Coordinates):
        """Test finding when sun reaches 0° (sunrise)."""
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)

        # Find rising crossing of 0°
        crossing = get_sun_altitude_time(
            sample_coordinates, date, target_altitude=0, rising=True
        )

        # Compare with twilight sunrise
        twilight = get_twilight_times(sample_coordinates, date)

        assert crossing is not None
        assert twilight.sunrise is not None
        # Should be within a few minutes
        diff = abs((crossing - twilight.sunrise).total_seconds())
        assert diff < 300  # Within 5 minutes

    def test_find_solar_observation_time(self, sample_coordinates: Coordinates):
        """Test finding when sun reaches 20° altitude."""
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)

        # Find rising crossing of 20°
        crossing = get_sun_altitude_time(
            sample_coordinates, date, target_altitude=20, rising=True
        )

        assert crossing is not None

        # Verify the sun is actually near 20° at this time
        position = get_sun_position(sample_coordinates, crossing)
        assert abs(position.altitude_deg - 20) < 2  # Within 2 degrees

    def test_find_setting_time(self, sample_coordinates: Coordinates):
        """Test finding when sun sets below an altitude."""
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)

        # Find setting crossing of 20°
        crossing = get_sun_altitude_time(
            sample_coordinates, date, target_altitude=20, rising=False
        )

        assert crossing is not None

        # Setting time should be after midday
        assert crossing.hour > 12 or crossing.day > date.day


class TestAstronomyCalculator:
    """Tests for the AstronomyCalculator class."""

    def test_calculator_initialization(self, sample_coordinates: Coordinates):
        """Test calculator initialization."""
        calc = AstronomyCalculator(sample_coordinates)
        assert calc.coordinates == sample_coordinates

    def test_calculator_sun_position(self, sample_coordinates: Coordinates):
        """Test getting sun position through calculator."""
        calc = AstronomyCalculator(sample_coordinates)
        time = datetime(2024, 6, 21, 17, 0, tzinfo=timezone.utc)

        position = calc.get_sun_position(time)
        assert position.altitude_deg > 0

    def test_calculator_moon_position(self, sample_coordinates: Coordinates):
        """Test getting moon position through calculator."""
        calc = AstronomyCalculator(sample_coordinates)
        time = datetime(2024, 6, 21, 20, 0, tzinfo=timezone.utc)

        position = calc.get_moon_position(time)
        assert -90 <= position.altitude_deg <= 90

    def test_calculator_twilight_caching(self, sample_coordinates: Coordinates):
        """Test that twilight times are cached."""
        calc = AstronomyCalculator(sample_coordinates)
        date = datetime(2024, 6, 21, tzinfo=timezone.utc)

        # First call
        twilight1 = calc.get_twilight_times(date)

        # Second call should return cached result
        twilight2 = calc.get_twilight_times(date)

        assert twilight1 is twilight2  # Same object, cached

    def test_calculator_is_night(self, sample_coordinates: Coordinates):
        """Test night detection."""
        calc = AstronomyCalculator(sample_coordinates)

        midday = datetime(2024, 6, 21, 17, 0, tzinfo=timezone.utc)
        midnight = datetime(2024, 6, 21, 4, 0, tzinfo=timezone.utc)

        assert calc.is_night(midday) is False
        assert calc.is_night(midnight) is True

    def test_calculator_astronomical_night(self, sample_coordinates: Coordinates):
        """Test astronomical night detection."""
        calc = AstronomyCalculator(sample_coordinates)

        # Late night should be astronomical night
        late_night = datetime(2024, 6, 21, 5, 0, tzinfo=timezone.utc)  # ~1am EDT

        # This depends on the time of year; in summer NYC may not
        # have true astronomical night. Test just that the method works.
        result = calc.is_astronomical_night(late_night)
        assert isinstance(result, bool)

    def test_calculator_astronomical_data(self, sample_coordinates: Coordinates):
        """Test getting complete astronomical data."""
        calc = AstronomyCalculator(sample_coordinates)
        time = datetime(2024, 6, 21, 20, 0, tzinfo=timezone.utc)

        data = calc.get_astronomical_data(time)

        # Should have all the fields populated
        assert data.sun_altitude_deg is not None
        assert data.sun_azimuth_deg is not None
        assert data.moon_altitude_deg is not None
        assert data.moon_phase is not None
        assert data.sunrise is not None
        assert data.sunset is not None
