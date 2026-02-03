"""Tests for location models."""

import pytest

from weather_events.models.location import Coordinates, Location


class TestCoordinates:
    """Tests for the Coordinates model."""

    def test_valid_coordinates(self):
        """Test creating valid coordinates."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        assert coords.latitude == 40.7128
        assert coords.longitude == -74.0060

    def test_boundary_values(self):
        """Test boundary latitude/longitude values."""
        # North pole
        north = Coordinates(latitude=90, longitude=0)
        assert north.latitude == 90

        # South pole
        south = Coordinates(latitude=-90, longitude=0)
        assert south.latitude == -90

        # Date line
        east = Coordinates(latitude=0, longitude=180)
        west = Coordinates(latitude=0, longitude=-180)
        assert east.longitude == 180
        assert west.longitude == -180

    def test_invalid_latitude(self):
        """Test that invalid latitude raises error."""
        with pytest.raises(ValueError):
            Coordinates(latitude=91, longitude=0)

        with pytest.raises(ValueError):
            Coordinates(latitude=-91, longitude=0)

    def test_invalid_longitude(self):
        """Test that invalid longitude raises error."""
        with pytest.raises(ValueError):
            Coordinates(latitude=0, longitude=181)

        with pytest.raises(ValueError):
            Coordinates(latitude=0, longitude=-181)

    def test_from_string_positive(self):
        """Test parsing coordinates from positive string."""
        coords = Coordinates.from_string("40.7128,-74.0060")
        assert coords.latitude == pytest.approx(40.7128)
        assert coords.longitude == pytest.approx(-74.0060)

    def test_from_string_with_plus_signs(self):
        """Test parsing coordinates with explicit plus signs."""
        coords = Coordinates.from_string("+40.7128,-74.0060")
        assert coords.latitude == pytest.approx(40.7128)
        assert coords.longitude == pytest.approx(-74.0060)

    def test_from_string_southern_hemisphere(self):
        """Test parsing coordinates in southern hemisphere."""
        # Sydney, Australia
        coords = Coordinates.from_string("-33.8688,151.2093")
        assert coords.latitude == pytest.approx(-33.8688)
        assert coords.longitude == pytest.approx(151.2093)

    def test_from_string_with_spaces(self):
        """Test parsing coordinates with spaces around comma."""
        coords = Coordinates.from_string("40.7128 , -74.0060")
        assert coords.latitude == pytest.approx(40.7128)

    def test_from_string_invalid_format(self):
        """Test that invalid format raises error."""
        with pytest.raises(ValueError, match="Invalid coordinate format"):
            Coordinates.from_string("not,valid")

        with pytest.raises(ValueError):
            Coordinates.from_string("40.7128")  # Missing longitude

    def test_str_representation(self):
        """Test string representation of coordinates."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        assert str(coords) == "40.7128,-74.006"

    def test_to_tuple(self):
        """Test converting to tuple."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        assert coords.to_tuple() == (40.7128, -74.0060)


class TestLocation:
    """Tests for the Location model."""

    def test_location_with_address(self):
        """Test creating location with address."""
        loc = Location(address="New York, NY")
        assert loc.address == "New York, NY"
        assert loc.coordinates is None

    def test_location_with_coordinates(self):
        """Test creating location with coordinates."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        loc = Location(coordinates=coords)
        assert loc.coordinates == coords
        assert loc.address is None

    def test_location_with_both(self):
        """Test creating location with both address and coordinates."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        loc = Location(address="New York, NY", coordinates=coords)
        assert loc.address == "New York, NY"
        assert loc.coordinates == coords

    def test_location_requires_something(self):
        """Test that location requires at least address or coordinates."""
        with pytest.raises(ValueError, match="Either address or coordinates"):
            Location()

    def test_from_coordinates(self):
        """Test creating location from coordinate values."""
        loc = Location.from_coordinates(40.7128, -74.0060, timezone="America/New_York")
        assert loc.coordinates is not None
        assert loc.coordinates.latitude == 40.7128
        assert loc.timezone == "America/New_York"

    def test_from_string_as_coordinates(self):
        """Test creating location from coordinate string."""
        loc = Location.from_string("40.7128,-74.0060")
        assert loc.coordinates is not None
        assert loc.coordinates.latitude == pytest.approx(40.7128)

    def test_from_string_as_address(self):
        """Test creating location from address string."""
        loc = Location.from_string("New York, NY")
        assert loc.address == "New York, NY"
        assert loc.coordinates is None

    def test_display_name_with_name(self):
        """Test display name returns custom name."""
        loc = Location(address="123 Main St", name="Home")
        assert loc.display_name() == "Home"

    def test_display_name_with_address(self):
        """Test display name returns address when no name."""
        loc = Location(address="123 Main St")
        assert loc.display_name() == "123 Main St"

    def test_display_name_with_coordinates(self):
        """Test display name returns coordinates when no name or address."""
        coords = Coordinates(latitude=40.7128, longitude=-74.0060)
        loc = Location(coordinates=coords)
        assert "40.7128" in loc.display_name()
