"""Location models for weather event recommendations."""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


# Regex for parsing lat/long coordinates: "latitude,longitude"
# Supports optional +/- prefix for both values
COORDINATE_PATTERN = re.compile(
    r"^(?P<lat>[-+]?\d*\.?\d+)\s*,\s*(?P<lon>[-+]?\d*\.?\d+)$"
)


class Coordinates(BaseModel):
    """Geographic coordinates (latitude/longitude).

    Latitude:
        - Negative (-) = south of equator
        - Positive (+) = north of equator
        - Range: -90 to +90

    Longitude:
        - Negative (-) = west of prime meridian
        - Positive (+) = east of prime meridian
        - Range: -180 to +180
    """

    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Parse coordinates from string format 'latitude,longitude'.

        Examples:
            '40.7128,-74.0060' -> New York City
            '-33.8688,151.2093' -> Sydney
            '+51.5074,-0.1278' -> London
        """
        match = COORDINATE_PATTERN.match(value.strip())
        if not match:
            raise ValueError(
                f"Invalid coordinate format: '{value}'. "
                "Expected format: 'latitude,longitude' (e.g., '40.7128,-74.0060')"
            )
        return cls(
            latitude=float(match.group("lat")),
            longitude=float(match.group("lon")),
        )

    def __str__(self) -> str:
        return f"{self.latitude},{self.longitude}"

    def to_tuple(self) -> tuple[float, float]:
        """Return coordinates as (latitude, longitude) tuple."""
        return (self.latitude, self.longitude)


class Location(BaseModel):
    """A location that can be specified by address or coordinates.

    At least one of address or coordinates must be provided.
    If both are provided, coordinates take precedence for weather lookups.
    """

    address: str | None = Field(
        default=None, description="Human-readable address or place name"
    )
    coordinates: Coordinates | None = Field(
        default=None, description="Geographic coordinates"
    )
    timezone: str | None = Field(
        default=None,
        description="IANA timezone identifier (e.g., 'America/New_York')",
    )
    name: str | None = Field(
        default=None, description="Optional friendly name for this location"
    )

    @model_validator(mode="after")
    def validate_has_location(self) -> Self:
        """Ensure at least one location identifier is provided."""
        if self.address is None and self.coordinates is None:
            raise ValueError("Either address or coordinates must be provided")
        return self

    @field_validator("address", mode="before")
    @classmethod
    def parse_address_or_coordinates(cls, v: str | None) -> str | None:
        """If address looks like coordinates, it will be parsed as such later."""
        return v

    @classmethod
    def from_coordinates(
        cls,
        latitude: float,
        longitude: float,
        timezone: str | None = None,
        name: str | None = None,
    ) -> Self:
        """Create a Location from latitude/longitude values."""
        return cls(
            coordinates=Coordinates(latitude=latitude, longitude=longitude),
            timezone=timezone,
            name=name,
        )

    @classmethod
    def from_string(cls, value: str, timezone: str | None = None) -> Self:
        """Create a Location from a string (address or coordinate string)."""
        # Try to parse as coordinates first
        try:
            coords = Coordinates.from_string(value)
            return cls(coordinates=coords, timezone=timezone)
        except ValueError:
            # Treat as address
            return cls(address=value, timezone=timezone)

    def get_coordinates(self) -> Coordinates | None:
        """Get coordinates, returning None if only address is available.

        Note: Address geocoding would need to be done separately.
        """
        return self.coordinates

    def display_name(self) -> str:
        """Get a display name for this location."""
        if self.name:
            return self.name
        if self.address:
            return self.address
        if self.coordinates:
            return str(self.coordinates)
        return "Unknown location"
