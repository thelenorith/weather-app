"""Go/No-Go decision systems for activities.

This module provides specialized evaluators that make go/no-go decisions
for activities based on weather conditions. Each evaluator can aggregate
multiple factors with different weights.

## Astronomy Go/No-Go Example

For astronomy club observing sessions, factors might include:
- Cloud cover (critical - blocks all observation)
- Precipitation probability (critical - equipment damage risk)
- Wind speed (important - affects telescope stability)
- Temperature (comfort/safety)
- Moon illumination (important for deep sky, less so for lunar)
- Transparency (atmosphere clarity)
- Seeing (atmospheric turbulence)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from weather_events.models.recommendation import (
    DecisionFactor,
    GoNoGoDecision,
    Severity,
)
from weather_events.models.weather import HourlyForecast


class DecisionWeight(Enum):
    """Weight categories for decision factors."""

    CRITICAL = 10  # Automatic NO_GO if failed
    HIGH = 7
    MEDIUM = 5
    LOW = 3
    MINIMAL = 1


@dataclass
class WeightedFactor:
    """A factor with weight and threshold for decision making."""

    name: str
    display_name: str
    weight: DecisionWeight
    threshold: float | None = None
    threshold_type: str = "max"  # "max", "min", "range"
    range_min: float | None = None
    range_max: float | None = None
    unit: str = ""
    is_blocking: bool = False  # If True, failure = automatic NO_GO

    def evaluate(self, value: float | None) -> tuple[bool, Severity]:
        """Evaluate if the value passes the threshold.

        Returns:
            Tuple of (passed, severity)
        """
        if value is None:
            return True, Severity.INFO  # Can't evaluate, don't penalize

        passed = True
        if self.threshold_type == "max" and self.threshold is not None:
            passed = value <= self.threshold
        elif self.threshold_type == "min" and self.threshold is not None:
            passed = value >= self.threshold
        elif self.threshold_type == "range":
            if self.range_min is not None:
                passed = passed and value >= self.range_min
            if self.range_max is not None:
                passed = passed and value <= self.range_max

        if passed:
            return True, Severity.GOOD
        elif self.is_blocking:
            return False, Severity.CRITICAL
        elif self.weight == DecisionWeight.CRITICAL:
            return False, Severity.CRITICAL
        elif self.weight == DecisionWeight.HIGH:
            return False, Severity.WARNING
        else:
            return False, Severity.CAUTION


class GoNoGoEvaluator:
    """Base class for go/no-go decision evaluators.

    Subclass this to create specialized evaluators for different activities.
    """

    def __init__(self, factors: list[WeightedFactor]):
        """Initialize with factors to evaluate.

        Args:
            factors: List of weighted factors for decision making
        """
        self.factors = factors

    def _extract_values(self, forecast: HourlyForecast) -> dict[str, float | None]:
        """Extract relevant values from forecast.

        Override in subclass to extract activity-specific values.
        """
        values: dict[str, float | None] = {}

        values["temperature"] = forecast.temperature_c
        values["feels_like"] = forecast.feels_like_c
        values["humidity"] = forecast.relative_humidity_percent

        if forecast.wind:
            values["wind_speed"] = forecast.wind.speed_ms
            values["wind_gust"] = forecast.wind.gust_ms
        else:
            values["wind_speed"] = None
            values["wind_gust"] = None

        if forecast.cloud_cover:
            values["cloud_cover"] = forecast.cloud_cover.total_percent
        else:
            values["cloud_cover"] = None

        if forecast.precipitation:
            values["precipitation_probability"] = forecast.precipitation.probability_percent
        else:
            values["precipitation_probability"] = 0

        values["visibility"] = forecast.visibility_m
        values["uv_index"] = forecast.uv_index

        return values

    def evaluate(self, forecast: HourlyForecast) -> GoNoGoDecision:
        """Evaluate forecast and make go/no-go decision.

        Args:
            forecast: Weather forecast to evaluate

        Returns:
            GoNoGoDecision with detailed factors
        """
        values = self._extract_values(forecast)
        decision_factors: list[DecisionFactor] = []
        blocking_factors: list[str] = []

        total_weight = 0.0
        weighted_score = 0.0

        for factor in self.factors:
            value = values.get(factor.name)
            passed, severity = factor.evaluate(value)

            decision_factors.append(
                DecisionFactor(
                    name=factor.name,
                    display_name=factor.display_name,
                    value=value if value is not None else "N/A",
                    unit=factor.unit,
                    threshold=factor.threshold,
                    is_acceptable=passed,
                    is_ideal=passed and severity == Severity.GOOD,
                    weight=factor.weight.value,
                    severity=severity,
                )
            )

            total_weight += factor.weight.value

            if passed:
                weighted_score += factor.weight.value * 100
            else:
                if factor.is_blocking or factor.weight == DecisionWeight.CRITICAL:
                    blocking_factors.append(factor.display_name)

        # Calculate final score
        score = weighted_score / total_weight if total_weight > 0 else 0

        # Determine decision
        if blocking_factors:
            decision = "NO_GO"
            summary = f"Blocked by: {', '.join(blocking_factors)}"
        elif score >= 70:
            decision = "GO"
            summary = "Conditions are favorable"
        elif score >= 50:
            decision = "MARGINAL"
            summary = "Conditions are acceptable but not ideal"
        else:
            decision = "NO_GO"
            summary = "Multiple factors below acceptable thresholds"

        # Generate recommendations
        recommendations: list[str] = []
        for df in decision_factors:
            if not df.is_acceptable:
                recommendations.append(f"Monitor {df.display_name}: currently {df.value}{df.unit}")

        return GoNoGoDecision(
            decision=decision,
            confidence=0.8,  # Could be improved with multiple data sources
            score=score,
            factors=decision_factors,
            blocking_factors=blocking_factors,
            summary=summary,
            recommendations=recommendations,
            valid_for=forecast.time,
        )


class AstronomyGoNoGoEvaluator(GoNoGoEvaluator):
    """Specialized evaluator for astronomy observing sessions.

    This evaluator is designed for making go/no-go decisions for astronomy
    club observing sessions, considering factors like:
    - Cloud cover (critical)
    - Precipitation (critical for equipment)
    - Wind (affects telescope stability)
    - Temperature (comfort/safety)
    - Moon (affects deep sky visibility)
    """

    def __init__(
        self,
        max_cloud_cover: float = 30,
        max_precipitation_prob: float = 20,
        max_wind_speed: float = 8,
        max_wind_gust: float = 12,
        min_temperature: float = -10,
        max_moon_illumination: float | None = None,
    ):
        """Initialize astronomy evaluator with thresholds.

        Args:
            max_cloud_cover: Maximum cloud cover % for GO
            max_precipitation_prob: Maximum precipitation probability %
            max_wind_speed: Maximum wind speed in m/s
            max_wind_gust: Maximum wind gust in m/s
            min_temperature: Minimum safe temperature in °C
            max_moon_illumination: Maximum moon illumination % (None = ignore)
        """
        factors = [
            WeightedFactor(
                name="cloud_cover",
                display_name="Cloud Cover",
                weight=DecisionWeight.CRITICAL,
                threshold=max_cloud_cover,
                threshold_type="max",
                unit="%",
                is_blocking=True,
            ),
            WeightedFactor(
                name="precipitation_probability",
                display_name="Precipitation Chance",
                weight=DecisionWeight.CRITICAL,
                threshold=max_precipitation_prob,
                threshold_type="max",
                unit="%",
                is_blocking=True,
            ),
            WeightedFactor(
                name="wind_speed",
                display_name="Wind Speed",
                weight=DecisionWeight.HIGH,
                threshold=max_wind_speed,
                threshold_type="max",
                unit=" m/s",
            ),
            WeightedFactor(
                name="wind_gust",
                display_name="Wind Gusts",
                weight=DecisionWeight.MEDIUM,
                threshold=max_wind_gust,
                threshold_type="max",
                unit=" m/s",
            ),
            WeightedFactor(
                name="temperature",
                display_name="Temperature",
                weight=DecisionWeight.MEDIUM,
                threshold=min_temperature,
                threshold_type="min",
                unit="°C",
            ),
        ]

        if max_moon_illumination is not None:
            factors.append(
                WeightedFactor(
                    name="moon_illumination",
                    display_name="Moon Illumination",
                    weight=DecisionWeight.LOW,
                    threshold=max_moon_illumination,
                    threshold_type="max",
                    unit="%",
                )
            )

        super().__init__(factors)

    def _extract_values(self, forecast: HourlyForecast) -> dict[str, Any]:
        """Extract astronomy-relevant values from forecast."""
        values = super()._extract_values(forecast)

        # Add moon illumination if available
        if forecast.astronomical:
            values["moon_illumination"] = forecast.astronomical.moon_illumination_percent
            values["sun_altitude"] = forecast.astronomical.sun_altitude_deg
        else:
            values["moon_illumination"] = None
            values["sun_altitude"] = None

        return values


class SolarObservingEvaluator(GoNoGoEvaluator):
    """Specialized evaluator for solar observation/imaging.

    Considers:
    - Cloud cover (must be very low)
    - Sun altitude (must be high enough)
    - Wind (affects imaging quality)
    """

    def __init__(
        self,
        max_cloud_cover: float = 15,
        min_sun_altitude: float = 20,
        max_wind_speed: float = 5,
    ):
        """Initialize solar observing evaluator.

        Args:
            max_cloud_cover: Maximum cloud cover % for clear sun
            min_sun_altitude: Minimum sun altitude in degrees
            max_wind_speed: Maximum wind speed in m/s
        """
        factors = [
            WeightedFactor(
                name="cloud_cover",
                display_name="Cloud Cover",
                weight=DecisionWeight.CRITICAL,
                threshold=max_cloud_cover,
                threshold_type="max",
                unit="%",
                is_blocking=True,
            ),
            WeightedFactor(
                name="sun_altitude",
                display_name="Sun Altitude",
                weight=DecisionWeight.CRITICAL,
                threshold=min_sun_altitude,
                threshold_type="min",
                unit="°",
                is_blocking=True,
            ),
            WeightedFactor(
                name="wind_speed",
                display_name="Wind Speed",
                weight=DecisionWeight.HIGH,
                threshold=max_wind_speed,
                threshold_type="max",
                unit=" m/s",
            ),
        ]

        super().__init__(factors)

    def _extract_values(self, forecast: HourlyForecast) -> dict[str, Any]:
        """Extract solar observation values from forecast."""
        values = super()._extract_values(forecast)

        if forecast.astronomical:
            values["sun_altitude"] = forecast.astronomical.sun_altitude_deg
        else:
            values["sun_altitude"] = None

        return values
