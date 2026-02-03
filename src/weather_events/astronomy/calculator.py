"""Astronomical calculations using astropy.

This module provides accurate calculations for:
- Sun position (altitude, azimuth)
- Moon position and phase
- Twilight times (civil, nautical, astronomical)
- Sunrise/sunset times
- Finding times when celestial bodies reach specific altitudes

All calculations use the astropy library for precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, get_body, get_sun
from astropy.time import Time

from weather_events.models.location import Coordinates
from weather_events.models.weather import AstronomicalData


@dataclass
class SunPosition:
    """Sun position at a specific time and location."""

    altitude_deg: float  # Degrees above horizon (negative = below)
    azimuth_deg: float  # Degrees from north (0=N, 90=E, 180=S, 270=W)
    time: datetime
    is_day: bool  # Sun above horizon


@dataclass
class MoonPosition:
    """Moon position and phase at a specific time and location."""

    altitude_deg: float
    azimuth_deg: float
    time: datetime
    phase: float  # 0 = new moon, 0.5 = full moon, 1 = new moon
    illumination_percent: float  # 0-100


@dataclass
class TwilightTimes:
    """Twilight and sun event times for a specific date and location."""

    date: datetime

    # Sun events
    sunrise: datetime | None  # Sun at 0° (horizon)
    sunset: datetime | None
    solar_noon: datetime | None

    # Civil twilight (sun at -6°)
    civil_twilight_start: datetime | None  # Morning, sun rising toward -6°
    civil_twilight_end: datetime | None  # Evening, sun setting past -6°

    # Nautical twilight (sun at -12°)
    nautical_twilight_start: datetime | None
    nautical_twilight_end: datetime | None

    # Astronomical twilight (sun at -18°)
    astronomical_twilight_start: datetime | None  # True darkness begins after this
    astronomical_twilight_end: datetime | None  # True darkness ends before this


def _coords_to_earth_location(coords: Coordinates) -> EarthLocation:
    """Convert our Coordinates to astropy EarthLocation."""
    return EarthLocation(lat=coords.latitude * u.deg, lon=coords.longitude * u.deg)


def _datetime_to_astropy_time(dt: datetime) -> Time:
    """Convert datetime to astropy Time."""
    return Time(dt)


def get_sun_position(coords: Coordinates, time: datetime) -> SunPosition:
    """Calculate sun position at a given time and location.

    Args:
        coords: Geographic coordinates
        time: Time to calculate position for (should be timezone-aware)

    Returns:
        SunPosition with altitude and azimuth in degrees
    """
    location = _coords_to_earth_location(coords)
    obs_time = _datetime_to_astropy_time(time)

    # Create the AltAz frame for this location and time
    altaz_frame = AltAz(obstime=obs_time, location=location)

    # Get the sun's position and transform to AltAz
    sun = get_sun(obs_time)
    sun_altaz = sun.transform_to(altaz_frame)

    altitude = float(sun_altaz.alt.deg)
    azimuth = float(sun_altaz.az.deg)

    return SunPosition(
        altitude_deg=altitude,
        azimuth_deg=azimuth,
        time=time,
        is_day=altitude > 0,
    )


def get_moon_position(coords: Coordinates, time: datetime) -> MoonPosition:
    """Calculate moon position and phase at a given time and location.

    Args:
        coords: Geographic coordinates
        time: Time to calculate position for

    Returns:
        MoonPosition with altitude, azimuth, phase, and illumination
    """
    location = _coords_to_earth_location(coords)
    obs_time = _datetime_to_astropy_time(time)

    # Create the AltAz frame
    altaz_frame = AltAz(obstime=obs_time, location=location)

    # Get moon position
    moon = get_body("moon", obs_time)
    moon_altaz = moon.transform_to(altaz_frame)

    altitude = float(moon_altaz.alt.deg)
    azimuth = float(moon_altaz.az.deg)

    # Calculate moon phase using sun-moon elongation
    sun = get_sun(obs_time)
    elongation = sun.separation(moon)
    phase = float((1 - elongation.deg / 180) / 2)  # 0 = new, 0.5 = full

    # Illumination is roughly related to phase
    # More accurate: use cos of elongation
    illumination = (1 - float(elongation.deg / 180)) * 100

    return MoonPosition(
        altitude_deg=altitude,
        azimuth_deg=azimuth,
        time=time,
        phase=phase,
        illumination_percent=max(0, min(100, illumination)),
    )


def _find_altitude_crossing(
    coords: Coordinates,
    start_time: datetime,
    end_time: datetime,
    target_altitude: float,
    rising: bool,
    body: Literal["sun", "moon"] = "sun",
    tolerance_minutes: float = 1.0,
) -> datetime | None:
    """Find when a celestial body crosses a specific altitude.

    Uses binary search to find the crossing time.

    Args:
        coords: Geographic coordinates
        start_time: Start of search window
        end_time: End of search window
        target_altitude: Target altitude in degrees
        rising: True if looking for rising crossing, False for setting
        body: 'sun' or 'moon'
        tolerance_minutes: Precision of result in minutes

    Returns:
        Time of crossing, or None if not found
    """
    location = _coords_to_earth_location(coords)

    def get_altitude(dt: datetime) -> float:
        obs_time = _datetime_to_astropy_time(dt)
        altaz_frame = AltAz(obstime=obs_time, location=location)
        if body == "sun":
            obj = get_sun(obs_time)
        else:
            obj = get_body("moon", obs_time)
        obj_altaz = obj.transform_to(altaz_frame)
        return float(obj_altaz.alt.deg)

    # Sample at 15-minute intervals to find bracket
    sample_interval = timedelta(minutes=15)
    current = start_time
    prev_alt = get_altitude(current)
    prev_time = current

    while current < end_time:
        current += sample_interval
        curr_alt = get_altitude(current)

        # Check if we crossed the target altitude
        crossed = False
        if rising and prev_alt < target_altitude <= curr_alt:
            crossed = True
        elif not rising and prev_alt > target_altitude >= curr_alt:
            crossed = True

        if crossed:
            # Binary search to find exact crossing
            low_time = prev_time
            high_time = current
            tolerance = timedelta(minutes=tolerance_minutes)

            while (high_time - low_time) > tolerance:
                mid_time = low_time + (high_time - low_time) / 2
                mid_alt = get_altitude(mid_time)

                if rising:
                    if mid_alt < target_altitude:
                        low_time = mid_time
                    else:
                        high_time = mid_time
                else:
                    if mid_alt > target_altitude:
                        low_time = mid_time
                    else:
                        high_time = mid_time

            return low_time + (high_time - low_time) / 2

        prev_alt = curr_alt
        prev_time = current

    return None


def get_twilight_times(coords: Coordinates, date: datetime) -> TwilightTimes:
    """Calculate twilight and sun event times for a specific date.

    Args:
        coords: Geographic coordinates
        date: Date to calculate for (time portion is ignored)

    Returns:
        TwilightTimes with all twilight boundaries and sun events
    """
    # Start from midnight local time (or UTC if no timezone)
    if date.tzinfo is not None:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)

    end = start + timedelta(days=1)

    # Solar noon is when sun is at maximum altitude
    # Approximate by finding midpoint between sunrise and sunset
    noon_approx = start + timedelta(hours=12)

    # Find sunrise (sun crossing 0° rising)
    sunrise = _find_altitude_crossing(coords, start, end, 0, rising=True, body="sun")

    # Find sunset (sun crossing 0° setting)
    sunset = _find_altitude_crossing(coords, start, end, 0, rising=False, body="sun")

    # Solar noon is approximately midpoint between sunrise and sunset
    solar_noon = None
    if sunrise and sunset:
        solar_noon = sunrise + (sunset - sunrise) / 2

    # Civil twilight (-6°)
    civil_start = _find_altitude_crossing(coords, start, end, -6, rising=True, body="sun")
    civil_end = _find_altitude_crossing(coords, start, end, -6, rising=False, body="sun")

    # Nautical twilight (-12°)
    nautical_start = _find_altitude_crossing(coords, start, end, -12, rising=True, body="sun")
    nautical_end = _find_altitude_crossing(coords, start, end, -12, rising=False, body="sun")

    # Astronomical twilight (-18°)
    astro_start = _find_altitude_crossing(coords, start, end, -18, rising=True, body="sun")
    astro_end = _find_altitude_crossing(coords, start, end, -18, rising=False, body="sun")

    return TwilightTimes(
        date=date,
        sunrise=sunrise,
        sunset=sunset,
        solar_noon=solar_noon,
        civil_twilight_start=civil_start,
        civil_twilight_end=civil_end,
        nautical_twilight_start=nautical_start,
        nautical_twilight_end=nautical_end,
        astronomical_twilight_start=astro_start,
        astronomical_twilight_end=astro_end,
    )


def get_sun_altitude_time(
    coords: Coordinates,
    date: datetime,
    target_altitude: float,
    rising: bool = True,
) -> datetime | None:
    """Find when the sun reaches a specific altitude.

    Useful for solar observation planning (e.g., sun > 20°).

    Args:
        coords: Geographic coordinates
        date: Date to search within
        target_altitude: Target altitude in degrees
        rising: True to find rising time, False for setting

    Returns:
        Time when sun reaches target altitude, or None
    """
    if date.tzinfo is not None:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)

    end = start + timedelta(days=1)

    return _find_altitude_crossing(
        coords, start, end, target_altitude, rising=rising, body="sun"
    )


class AstronomyCalculator:
    """Calculator for astronomical data at a specific location.

    This class provides a convenient interface for getting astronomical
    data for a fixed location, caching intermediate results.

    Example:
        ```python
        calc = AstronomyCalculator(Coordinates(latitude=40.7128, longitude=-74.0060))

        # Get twilight times for today
        twilight = calc.get_twilight_times(datetime.now())

        # Get sun position right now
        sun = calc.get_sun_position(datetime.now())

        # Find when sun reaches 20° altitude
        solar_time = calc.get_sun_altitude_time(datetime.now(), 20)
        ```
    """

    def __init__(self, coordinates: Coordinates):
        """Initialize calculator for a specific location.

        Args:
            coordinates: Geographic coordinates for calculations
        """
        self.coordinates = coordinates
        self._twilight_cache: dict[str, TwilightTimes] = {}

    def get_sun_position(self, time: datetime) -> SunPosition:
        """Get sun position at the given time."""
        return get_sun_position(self.coordinates, time)

    def get_moon_position(self, time: datetime) -> MoonPosition:
        """Get moon position at the given time."""
        return get_moon_position(self.coordinates, time)

    def get_twilight_times(self, date: datetime) -> TwilightTimes:
        """Get twilight times for a date (cached)."""
        cache_key = date.date().isoformat()
        if cache_key not in self._twilight_cache:
            self._twilight_cache[cache_key] = get_twilight_times(
                self.coordinates, date
            )
        return self._twilight_cache[cache_key]

    def get_sun_altitude_time(
        self,
        date: datetime,
        target_altitude: float,
        rising: bool = True,
    ) -> datetime | None:
        """Find when sun reaches a specific altitude."""
        return get_sun_altitude_time(
            self.coordinates, date, target_altitude, rising
        )

    def get_astronomical_data(self, time: datetime) -> AstronomicalData:
        """Get complete astronomical data for a specific time.

        Returns a populated AstronomicalData model suitable for inclusion
        in weather forecasts.
        """
        sun = self.get_sun_position(time)
        moon = self.get_moon_position(time)
        twilight = self.get_twilight_times(time)

        return AstronomicalData(
            sunrise=twilight.sunrise,
            sunset=twilight.sunset,
            solar_noon=twilight.solar_noon,
            civil_twilight_start=twilight.civil_twilight_start,
            civil_twilight_end=twilight.civil_twilight_end,
            nautical_twilight_start=twilight.nautical_twilight_start,
            nautical_twilight_end=twilight.nautical_twilight_end,
            astronomical_twilight_start=twilight.astronomical_twilight_start,
            astronomical_twilight_end=twilight.astronomical_twilight_end,
            sun_altitude_deg=sun.altitude_deg,
            sun_azimuth_deg=sun.azimuth_deg,
            moon_altitude_deg=moon.altitude_deg,
            moon_phase=moon.phase,
            moon_illumination_percent=moon.illumination_percent,
        )

    def is_astronomical_night(self, time: datetime) -> bool:
        """Check if it's astronomical night (sun below -18°)."""
        sun = self.get_sun_position(time)
        return sun.altitude_deg < -18

    def is_night(self, time: datetime) -> bool:
        """Check if it's night (sun below horizon)."""
        sun = self.get_sun_position(time)
        return sun.altitude_deg < 0
