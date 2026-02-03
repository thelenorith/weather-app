"""Condition definitions for the rule engine.

Conditions are individual rules that can be evaluated against weather data.
They can be combined using AND/OR logic to create complex requirements.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from weather_events.models.weather import HourlyForecast


class ConditionType(str, Enum):
    """Types of weather conditions that can be evaluated."""

    # Temperature
    TEMPERATURE = "temperature"
    FEELS_LIKE = "feels_like"
    DEW_POINT = "dew_point"

    # Humidity
    HUMIDITY = "humidity"

    # Wind
    WIND_SPEED = "wind_speed"
    WIND_GUST = "wind_gust"
    WIND_DIRECTION = "wind_direction"

    # Clouds
    CLOUD_COVER = "cloud_cover"
    CLOUD_COVER_LOW = "cloud_cover_low"
    CLOUD_COVER_HIGH = "cloud_cover_high"

    # Precipitation
    PRECIPITATION_PROBABILITY = "precipitation_probability"
    PRECIPITATION_AMOUNT = "precipitation_amount"

    # Visibility
    VISIBILITY = "visibility"

    # UV
    UV_INDEX = "uv_index"

    # Pressure
    PRESSURE = "pressure"

    # Astronomy
    SUN_ALTITUDE = "sun_altitude"
    MOON_ALTITUDE = "moon_altitude"
    MOON_ILLUMINATION = "moon_illumination"
    IS_NIGHT = "is_night"
    IS_ASTRONOMICAL_NIGHT = "is_astronomical_night"

    # Weather condition
    WEATHER_CONDITION = "weather_condition"


class ComparisonOperator(str, Enum):
    """Operators for comparing values."""

    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    EQUAL = "eq"
    NOT_EQUAL = "neq"
    IN = "in"  # Value is in a list
    NOT_IN = "not_in"  # Value is not in a list
    BETWEEN = "between"  # Value is between two values


class ConditionResult(BaseModel):
    """Result of evaluating a single condition."""

    condition_type: ConditionType
    passed: bool
    actual_value: Any
    expected_value: Any
    operator: ComparisonOperator
    message: str
    severity: float = Field(
        default=1.0,
        ge=0,
        le=10,
        description="How severe the violation is (0=minor, 10=critical)",
    )


class Condition(BaseModel):
    """A single condition to evaluate against weather data.

    Conditions define what weather values are acceptable for an activity.
    They can be evaluated against HourlyForecast data.

    Example:
        ```python
        # Temperature must be above 5°C
        temp_condition = Condition(
            type=ConditionType.TEMPERATURE,
            operator=ComparisonOperator.GREATER_THAN,
            value=5,
            description="Temperature above freezing",
        )

        # Wind must be below 10 m/s
        wind_condition = Condition(
            type=ConditionType.WIND_SPEED,
            operator=ComparisonOperator.LESS_THAN,
            value=10,
            description="Calm wind",
        )
        ```
    """

    type: ConditionType = Field(..., description="Type of condition to evaluate")
    operator: ComparisonOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    description: str | None = Field(default=None, description="Human-readable description")
    is_required: bool = Field(
        default=True, description="If True, failure blocks the activity"
    )
    weight: float = Field(
        default=1.0, ge=0, le=10, description="Weight in scoring calculations"
    )
    severity_on_fail: float = Field(
        default=5.0, ge=0, le=10, description="Severity if condition fails"
    )

    def evaluate(self, forecast: HourlyForecast) -> ConditionResult:
        """Evaluate this condition against forecast data.

        Args:
            forecast: Hourly forecast data to evaluate

        Returns:
            ConditionResult with pass/fail and details
        """
        actual = self._extract_value(forecast)
        passed = self._compare(actual, self.value)

        if passed:
            message = f"{self.type.value}: {actual} meets requirement"
        else:
            message = (
                f"{self.type.value}: {actual} does not meet "
                f"{self.operator.value} {self.value}"
            )

        return ConditionResult(
            condition_type=self.type,
            passed=passed,
            actual_value=actual,
            expected_value=self.value,
            operator=self.operator,
            message=message,
            severity=0 if passed else self.severity_on_fail,
        )

    def _extract_value(self, forecast: HourlyForecast) -> Any:
        """Extract the relevant value from forecast data."""
        extractors = {
            ConditionType.TEMPERATURE: lambda f: f.temperature_c,
            ConditionType.FEELS_LIKE: lambda f: f.feels_like_c,
            ConditionType.DEW_POINT: lambda f: f.dew_point_c,
            ConditionType.HUMIDITY: lambda f: f.relative_humidity_percent,
            ConditionType.WIND_SPEED: lambda f: f.wind.speed_ms if f.wind else None,
            ConditionType.WIND_GUST: lambda f: f.wind.gust_ms if f.wind else None,
            ConditionType.WIND_DIRECTION: lambda f: (
                f.wind.direction_deg if f.wind else None
            ),
            ConditionType.CLOUD_COVER: lambda f: (
                f.cloud_cover.total_percent if f.cloud_cover else None
            ),
            ConditionType.CLOUD_COVER_LOW: lambda f: (
                f.cloud_cover.low_percent if f.cloud_cover else None
            ),
            ConditionType.CLOUD_COVER_HIGH: lambda f: (
                f.cloud_cover.high_percent if f.cloud_cover else None
            ),
            ConditionType.PRECIPITATION_PROBABILITY: lambda f: (
                f.precipitation.probability_percent if f.precipitation else 0
            ),
            ConditionType.PRECIPITATION_AMOUNT: lambda f: (
                f.precipitation.amount_mm if f.precipitation else 0
            ),
            ConditionType.VISIBILITY: lambda f: f.visibility_m,
            ConditionType.UV_INDEX: lambda f: f.uv_index,
            ConditionType.PRESSURE: lambda f: f.pressure_hpa,
            ConditionType.SUN_ALTITUDE: lambda f: (
                f.astronomical.sun_altitude_deg if f.astronomical else None
            ),
            ConditionType.MOON_ALTITUDE: lambda f: (
                f.astronomical.moon_altitude_deg if f.astronomical else None
            ),
            ConditionType.MOON_ILLUMINATION: lambda f: (
                f.astronomical.moon_illumination_percent if f.astronomical else None
            ),
            ConditionType.IS_NIGHT: lambda f: (
                f.astronomical.is_night() if f.astronomical else None
            ),
            ConditionType.IS_ASTRONOMICAL_NIGHT: lambda f: (
                f.astronomical.is_astronomical_night() if f.astronomical else None
            ),
            ConditionType.WEATHER_CONDITION: lambda f: f.condition.value,
        }

        extractor = extractors.get(self.type)
        if extractor:
            return extractor(forecast)
        return None

    def _compare(self, actual: Any, expected: Any) -> bool:
        """Compare actual value against expected using the operator."""
        if actual is None:
            return False  # Can't compare with None

        comparisons = {
            ComparisonOperator.LESS_THAN: lambda a, e: a < e,
            ComparisonOperator.LESS_THAN_OR_EQUAL: lambda a, e: a <= e,
            ComparisonOperator.GREATER_THAN: lambda a, e: a > e,
            ComparisonOperator.GREATER_THAN_OR_EQUAL: lambda a, e: a >= e,
            ComparisonOperator.EQUAL: lambda a, e: a == e,
            ComparisonOperator.NOT_EQUAL: lambda a, e: a != e,
            ComparisonOperator.IN: lambda a, e: a in e,
            ComparisonOperator.NOT_IN: lambda a, e: a not in e,
            ComparisonOperator.BETWEEN: lambda a, e: e[0] <= a <= e[1],
        }

        comparator = comparisons.get(self.operator)
        if comparator:
            try:
                return comparator(actual, expected)
            except (TypeError, IndexError):
                return False
        return False


def create_temperature_range_conditions(
    min_c: float | None = None,
    max_c: float | None = None,
    ideal_min_c: float | None = None,
    ideal_max_c: float | None = None,
) -> list[Condition]:
    """Create temperature range conditions.

    Args:
        min_c: Minimum acceptable temperature
        max_c: Maximum acceptable temperature
        ideal_min_c: Minimum ideal temperature (warning only)
        ideal_max_c: Maximum ideal temperature (warning only)

    Returns:
        List of Condition objects
    """
    conditions = []

    if min_c is not None:
        conditions.append(
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                value=min_c,
                description=f"Temperature at least {min_c}°C",
                is_required=True,
                severity_on_fail=8.0,
            )
        )

    if max_c is not None:
        conditions.append(
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                value=max_c,
                description=f"Temperature at most {max_c}°C",
                is_required=True,
                severity_on_fail=8.0,
            )
        )

    if ideal_min_c is not None:
        conditions.append(
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                value=ideal_min_c,
                description=f"Ideally above {ideal_min_c}°C",
                is_required=False,
                severity_on_fail=3.0,
            )
        )

    if ideal_max_c is not None:
        conditions.append(
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                value=ideal_max_c,
                description=f"Ideally below {ideal_max_c}°C",
                is_required=False,
                severity_on_fail=3.0,
            )
        )

    return conditions


def create_astronomy_conditions(
    require_night: bool = False,
    require_astronomical_night: bool = False,
    max_moon_illumination: float | None = None,
    max_cloud_cover: float | None = None,
) -> list[Condition]:
    """Create conditions for astronomy activities.

    Args:
        require_night: Require sun below horizon
        require_astronomical_night: Require sun below -18°
        max_moon_illumination: Maximum moon illumination percent
        max_cloud_cover: Maximum cloud cover percent

    Returns:
        List of Condition objects
    """
    conditions = []

    if require_night:
        conditions.append(
            Condition(
                type=ConditionType.IS_NIGHT,
                operator=ComparisonOperator.EQUAL,
                value=True,
                description="Nighttime required",
                is_required=True,
                severity_on_fail=10.0,
            )
        )

    if require_astronomical_night:
        conditions.append(
            Condition(
                type=ConditionType.IS_ASTRONOMICAL_NIGHT,
                operator=ComparisonOperator.EQUAL,
                value=True,
                description="Astronomical night required (sun below -18°)",
                is_required=True,
                severity_on_fail=10.0,
            )
        )

    if max_moon_illumination is not None:
        conditions.append(
            Condition(
                type=ConditionType.MOON_ILLUMINATION,
                operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                value=max_moon_illumination,
                description=f"Moon illumination at most {max_moon_illumination}%",
                is_required=False,
                severity_on_fail=4.0,
            )
        )

    if max_cloud_cover is not None:
        conditions.append(
            Condition(
                type=ConditionType.CLOUD_COVER,
                operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                value=max_cloud_cover,
                description=f"Cloud cover at most {max_cloud_cover}%",
                is_required=True,
                severity_on_fail=9.0,
            )
        )

    return conditions
