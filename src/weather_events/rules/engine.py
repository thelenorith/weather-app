"""Rule engine for evaluating weather conditions against activity requirements.

The rule engine takes a set of conditions and evaluates them against weather
forecast data to determine if conditions are suitable for an activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from weather_events.models.activity import Activity, ActivityRequirements
from weather_events.models.recommendation import (
    DecisionFactor,
    GoNoGoDecision,
    Severity,
)
from weather_events.models.weather import HourlyForecast
from weather_events.rules.conditions import (
    ComparisonOperator,
    Condition,
    ConditionResult,
    ConditionType,
)


@dataclass
class EvaluationResult:
    """Result of evaluating all conditions for a forecast."""

    forecast: HourlyForecast
    results: list[ConditionResult] = field(default_factory=list)
    score: float = 100.0  # 0-100, 100 = perfect conditions
    passed: bool = True  # All required conditions passed
    blocking_conditions: list[ConditionResult] = field(default_factory=list)

    @property
    def failed_required(self) -> list[ConditionResult]:
        """Get failed required conditions."""
        return self.blocking_conditions

    @property
    def all_passed(self) -> list[ConditionResult]:
        """Get all passed conditions."""
        return [r for r in self.results if r.passed]

    @property
    def all_failed(self) -> list[ConditionResult]:
        """Get all failed conditions."""
        return [r for r in self.results if not r.passed]


def evaluate_conditions(
    forecast: HourlyForecast,
    conditions: list[Condition],
) -> EvaluationResult:
    """Evaluate a forecast against a set of conditions.

    Args:
        forecast: Weather forecast data to evaluate
        conditions: List of conditions to check

    Returns:
        EvaluationResult with pass/fail and scoring
    """
    results: list[ConditionResult] = []
    blocking: list[ConditionResult] = []
    total_weight = 0.0
    weighted_score = 0.0

    for condition in conditions:
        result = condition.evaluate(forecast)
        results.append(result)
        total_weight += condition.weight

        if result.passed:
            weighted_score += condition.weight * 100
        else:
            # Partial score based on severity
            # Lower severity = higher partial score
            partial = max(0, 100 - result.severity * 10)
            weighted_score += condition.weight * partial

            if condition.is_required:
                blocking.append(result)

    # Calculate final score
    score = weighted_score / total_weight if total_weight > 0 else 100.0
    passed = len(blocking) == 0

    return EvaluationResult(
        forecast=forecast,
        results=results,
        score=score,
        passed=passed,
        blocking_conditions=blocking,
    )


class RuleEngine:
    """Engine for evaluating weather conditions against activity requirements.

    The RuleEngine converts activity requirements into conditions and evaluates
    them against weather forecasts to produce recommendations.

    Example:
        ```python
        engine = RuleEngine()

        # Evaluate a single forecast
        result = engine.evaluate_forecast(forecast, activity)

        # Evaluate multiple forecasts to find the best
        best = engine.find_best_time(forecasts, activity)

        # Get a go/no-go decision
        decision = engine.make_decision(forecast, activity)
        ```
    """

    def __init__(self):
        """Initialize the rule engine."""
        self._condition_cache: dict[str, list[Condition]] = {}

    def requirements_to_conditions(
        self, requirements: ActivityRequirements
    ) -> list[Condition]:
        """Convert activity requirements to evaluatable conditions.

        Args:
            requirements: Activity requirements to convert

        Returns:
            List of Condition objects
        """
        conditions: list[Condition] = []

        # Temperature conditions
        if requirements.temperature:
            temp = requirements.temperature
            if temp.min_c is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.TEMPERATURE,
                        operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                        value=temp.min_c,
                        description=f"Temperature at least {temp.min_c}°C",
                        is_required=True,
                        severity_on_fail=8.0,
                    )
                )
            if temp.max_c is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.TEMPERATURE,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=temp.max_c,
                        description=f"Temperature at most {temp.max_c}°C",
                        is_required=True,
                        severity_on_fail=8.0,
                    )
                )
            if temp.ideal_min_c is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.TEMPERATURE,
                        operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                        value=temp.ideal_min_c,
                        description=f"Ideally above {temp.ideal_min_c}°C",
                        is_required=False,
                        severity_on_fail=2.0,
                        weight=0.5,
                    )
                )
            if temp.ideal_max_c is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.TEMPERATURE,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=temp.ideal_max_c,
                        description=f"Ideally below {temp.ideal_max_c}°C",
                        is_required=False,
                        severity_on_fail=2.0,
                        weight=0.5,
                    )
                )

        # Wind conditions
        if requirements.wind:
            wind = requirements.wind
            if wind.max_speed_ms is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.WIND_SPEED,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=wind.max_speed_ms,
                        description=f"Wind at most {wind.max_speed_ms} m/s",
                        is_required=True,
                        severity_on_fail=7.0,
                    )
                )
            if wind.max_gust_ms is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.WIND_GUST,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=wind.max_gust_ms,
                        description=f"Gusts at most {wind.max_gust_ms} m/s",
                        is_required=True,
                        severity_on_fail=7.0,
                    )
                )
            if wind.ideal_max_speed_ms is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.WIND_SPEED,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=wind.ideal_max_speed_ms,
                        description=f"Ideally wind below {wind.ideal_max_speed_ms} m/s",
                        is_required=False,
                        severity_on_fail=2.0,
                        weight=0.5,
                    )
                )

        # Cloud conditions
        if requirements.clouds:
            clouds = requirements.clouds
            if clouds.max_total_percent is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.CLOUD_COVER,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=clouds.max_total_percent,
                        description=f"Cloud cover at most {clouds.max_total_percent}%",
                        is_required=True,
                        severity_on_fail=8.0,
                    )
                )
            if clouds.ideal_max_total_percent is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.CLOUD_COVER,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=clouds.ideal_max_total_percent,
                        description=f"Ideally clouds below {clouds.ideal_max_total_percent}%",
                        is_required=False,
                        severity_on_fail=2.0,
                        weight=0.5,
                    )
                )

        # Precipitation conditions
        if requirements.precipitation:
            precip = requirements.precipitation
            if precip.max_probability_percent is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.PRECIPITATION_PROBABILITY,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=precip.max_probability_percent,
                        description=f"Precipitation chance at most {precip.max_probability_percent}%",
                        is_required=True,
                        severity_on_fail=6.0,
                    )
                )

        # Visibility conditions
        if requirements.min_visibility_m is not None:
            conditions.append(
                Condition(
                    type=ConditionType.VISIBILITY,
                    operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                    value=requirements.min_visibility_m,
                    description=f"Visibility at least {requirements.min_visibility_m}m",
                    is_required=True,
                    severity_on_fail=5.0,
                )
            )

        # Sun conditions
        if requirements.sun:
            sun = requirements.sun
            if sun.require_below_horizon:
                conditions.append(
                    Condition(
                        type=ConditionType.SUN_ALTITUDE,
                        operator=ComparisonOperator.LESS_THAN,
                        value=0,
                        description="Sun below horizon",
                        is_required=True,
                        severity_on_fail=10.0,
                    )
                )
            if sun.require_astronomical_twilight:
                conditions.append(
                    Condition(
                        type=ConditionType.SUN_ALTITUDE,
                        operator=ComparisonOperator.LESS_THAN,
                        value=-18,
                        description="Astronomical twilight (sun below -18°)",
                        is_required=True,
                        severity_on_fail=10.0,
                    )
                )
            if sun.min_altitude_deg is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.SUN_ALTITUDE,
                        operator=ComparisonOperator.GREATER_THAN_OR_EQUAL,
                        value=sun.min_altitude_deg,
                        description=f"Sun at least {sun.min_altitude_deg}° above horizon",
                        is_required=True,
                        severity_on_fail=10.0,
                    )
                )
            if sun.max_altitude_deg is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.SUN_ALTITUDE,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=sun.max_altitude_deg,
                        description=f"Sun at most {sun.max_altitude_deg}° above horizon",
                        is_required=True,
                        severity_on_fail=10.0,
                    )
                )

        # Moon conditions
        if requirements.moon:
            moon = requirements.moon
            if moon.max_illumination_percent is not None:
                conditions.append(
                    Condition(
                        type=ConditionType.MOON_ILLUMINATION,
                        operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                        value=moon.max_illumination_percent,
                        description=f"Moon illumination at most {moon.max_illumination_percent}%",
                        is_required=False,
                        severity_on_fail=3.0,
                        weight=0.7,
                    )
                )
            if moon.require_below_horizon:
                conditions.append(
                    Condition(
                        type=ConditionType.MOON_ALTITUDE,
                        operator=ComparisonOperator.LESS_THAN,
                        value=0,
                        description="Moon below horizon",
                        is_required=False,
                        severity_on_fail=2.0,
                        weight=0.5,
                    )
                )

        # UV conditions
        if requirements.max_uv_index is not None:
            conditions.append(
                Condition(
                    type=ConditionType.UV_INDEX,
                    operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
                    value=requirements.max_uv_index,
                    description=f"UV index at most {requirements.max_uv_index}",
                    is_required=True,
                    severity_on_fail=6.0,
                )
            )

        return conditions

    def get_conditions_for_activity(self, activity: Activity) -> list[Condition]:
        """Get or create conditions for an activity (cached).

        Args:
            activity: Activity to get conditions for

        Returns:
            List of conditions for the activity
        """
        if activity.id not in self._condition_cache:
            self._condition_cache[activity.id] = self.requirements_to_conditions(
                activity.requirements
            )
        return self._condition_cache[activity.id]

    def evaluate_forecast(
        self,
        forecast: HourlyForecast,
        activity: Activity,
    ) -> EvaluationResult:
        """Evaluate a single forecast against activity requirements.

        Args:
            forecast: Forecast data to evaluate
            activity: Activity with requirements to check

        Returns:
            EvaluationResult with pass/fail and scoring
        """
        conditions = self.get_conditions_for_activity(activity)
        return evaluate_conditions(forecast, conditions)

    def evaluate_forecasts(
        self,
        forecasts: list[HourlyForecast],
        activity: Activity,
    ) -> list[EvaluationResult]:
        """Evaluate multiple forecasts against activity requirements.

        Args:
            forecasts: List of forecast data
            activity: Activity with requirements to check

        Returns:
            List of EvaluationResults, one per forecast
        """
        return [self.evaluate_forecast(f, activity) for f in forecasts]

    def find_best_time(
        self,
        forecasts: list[HourlyForecast],
        activity: Activity,
        require_passing: bool = True,
    ) -> EvaluationResult | None:
        """Find the best time slot from multiple forecasts.

        Args:
            forecasts: List of forecast data
            activity: Activity with requirements to check
            require_passing: Only consider forecasts that pass all requirements

        Returns:
            Best EvaluationResult, or None if no suitable time found
        """
        results = self.evaluate_forecasts(forecasts, activity)

        if require_passing:
            results = [r for r in results if r.passed]

        if not results:
            return None

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[0]

    def make_decision(
        self,
        forecast: HourlyForecast,
        activity: Activity,
    ) -> GoNoGoDecision:
        """Make a go/no-go decision for an activity.

        Args:
            forecast: Forecast data to evaluate
            activity: Activity with requirements to check

        Returns:
            GoNoGoDecision with detailed factors
        """
        result = self.evaluate_forecast(forecast, activity)

        # Build decision factors
        factors: list[DecisionFactor] = []
        for cond_result in result.results:
            severity = Severity.GOOD if cond_result.passed else Severity.WARNING
            if not cond_result.passed and cond_result.severity >= 8:
                severity = Severity.CRITICAL

            factors.append(
                DecisionFactor(
                    name=cond_result.condition_type.value,
                    display_name=cond_result.condition_type.value.replace("_", " ").title(),
                    value=cond_result.actual_value,
                    threshold=cond_result.expected_value,
                    is_acceptable=cond_result.passed,
                    is_ideal=cond_result.passed and cond_result.severity == 0,
                    severity=severity,
                    notes=cond_result.message,
                )
            )

        # Determine decision
        if result.passed:
            if result.score >= 80:
                decision = "GO"
                summary = f"Conditions are favorable for {activity.name}"
            else:
                decision = "MARGINAL"
                summary = f"Conditions are acceptable but not ideal for {activity.name}"
        else:
            decision = "NO_GO"
            blocking_names = [b.condition_type.value for b in result.blocking_conditions]
            summary = f"Conditions not suitable: {', '.join(blocking_names)}"

        # Calculate confidence based on data availability
        non_none_count = sum(
            1 for r in result.results if r.actual_value is not None
        )
        confidence = non_none_count / len(result.results) if result.results else 0.5

        recommendations: list[str] = []
        for blocked in result.blocking_conditions:
            recommendations.append(f"Check {blocked.condition_type.value}: {blocked.message}")

        return GoNoGoDecision(
            decision=decision,
            confidence=confidence,
            score=result.score,
            factors=factors,
            blocking_factors=[b.condition_type.value for b in result.blocking_conditions],
            summary=summary,
            recommendations=recommendations,
            valid_for=forecast.time,
        )
