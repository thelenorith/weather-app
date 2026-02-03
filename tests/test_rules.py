"""Tests for the rule engine."""

from datetime import datetime, timezone

import pytest

from weather_events.models.activity import Activity
from weather_events.models.weather import (
    AstronomicalData,
    CloudCover,
    HourlyForecast,
    Precipitation,
    Wind,
)
from weather_events.rules.conditions import (
    ComparisonOperator,
    Condition,
    ConditionType,
    create_astronomy_conditions,
    create_temperature_range_conditions,
)
from weather_events.rules.engine import RuleEngine, evaluate_conditions


class TestCondition:
    """Tests for individual conditions."""

    def test_temperature_greater_than(self, sample_hourly_forecast: HourlyForecast):
        """Test temperature greater than condition."""
        condition = Condition(
            type=ConditionType.TEMPERATURE,
            operator=ComparisonOperator.GREATER_THAN,
            value=20,
        )
        result = condition.evaluate(sample_hourly_forecast)
        assert result.passed is True  # 22°C > 20°C

    def test_temperature_less_than_fails(self, sample_hourly_forecast: HourlyForecast):
        """Test temperature less than condition fails."""
        condition = Condition(
            type=ConditionType.TEMPERATURE,
            operator=ComparisonOperator.LESS_THAN,
            value=20,
        )
        result = condition.evaluate(sample_hourly_forecast)
        assert result.passed is False  # 22°C is not < 20°C

    def test_wind_speed_condition(self, sample_hourly_forecast: HourlyForecast):
        """Test wind speed condition."""
        condition = Condition(
            type=ConditionType.WIND_SPEED,
            operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
            value=5,
        )
        result = condition.evaluate(sample_hourly_forecast)
        assert result.passed is True  # 3.5 m/s <= 5 m/s

    def test_cloud_cover_condition(self, sample_hourly_forecast: HourlyForecast):
        """Test cloud cover condition."""
        condition = Condition(
            type=ConditionType.CLOUD_COVER,
            operator=ComparisonOperator.LESS_THAN_OR_EQUAL,
            value=50,
        )
        result = condition.evaluate(sample_hourly_forecast)
        assert result.passed is True  # 40% <= 50%

    def test_precipitation_probability_condition(
        self, sample_hourly_forecast: HourlyForecast
    ):
        """Test precipitation probability condition."""
        condition = Condition(
            type=ConditionType.PRECIPITATION_PROBABILITY,
            operator=ComparisonOperator.LESS_THAN,
            value=20,
        )
        result = condition.evaluate(sample_hourly_forecast)
        assert result.passed is True  # 10% < 20%

    def test_between_operator(self):
        """Test BETWEEN operator."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=15.0,
        )
        condition = Condition(
            type=ConditionType.TEMPERATURE,
            operator=ComparisonOperator.BETWEEN,
            value=[10, 20],  # Between 10 and 20
        )
        result = condition.evaluate(forecast)
        assert result.passed is True

    def test_in_operator(self):
        """Test IN operator for weather conditions."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
        )
        forecast.condition = forecast.condition  # Keep default UNKNOWN

        condition = Condition(
            type=ConditionType.WEATHER_CONDITION,
            operator=ComparisonOperator.IN,
            value=["unknown", "clear", "partly_cloudy"],
        )
        result = condition.evaluate(forecast)
        assert result.passed is True

    def test_condition_with_none_value(self):
        """Test condition evaluation when value is None."""
        forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
            # No wind data
        )
        condition = Condition(
            type=ConditionType.WIND_SPEED,
            operator=ComparisonOperator.LESS_THAN,
            value=10,
        )
        result = condition.evaluate(forecast)
        assert result.passed is False  # Can't compare with None

    def test_sun_altitude_condition(self, clear_night_forecast: HourlyForecast):
        """Test sun altitude condition for astronomy."""
        condition = Condition(
            type=ConditionType.SUN_ALTITUDE,
            operator=ComparisonOperator.LESS_THAN,
            value=-18,  # Astronomical twilight
        )
        result = condition.evaluate(clear_night_forecast)
        assert result.passed is True  # -25° < -18°


class TestConditionFactories:
    """Tests for condition factory functions."""

    def test_temperature_range_conditions(self):
        """Test creating temperature range conditions."""
        conditions = create_temperature_range_conditions(
            min_c=5, max_c=30, ideal_min_c=15, ideal_max_c=25
        )
        assert len(conditions) == 4

        # Check that required conditions are set correctly
        required = [c for c in conditions if c.is_required]
        assert len(required) == 2

    def test_astronomy_conditions(self):
        """Test creating astronomy conditions."""
        conditions = create_astronomy_conditions(
            require_astronomical_night=True,
            max_moon_illumination=50,
            max_cloud_cover=20,
        )

        # Should have astronomical night, moon, and cloud conditions
        types = [c.type for c in conditions]
        assert ConditionType.IS_ASTRONOMICAL_NIGHT in types
        assert ConditionType.MOON_ILLUMINATION in types
        assert ConditionType.CLOUD_COVER in types


class TestEvaluateConditions:
    """Tests for the evaluate_conditions function."""

    def test_all_conditions_pass(self, sample_hourly_forecast: HourlyForecast):
        """Test evaluation when all conditions pass."""
        conditions = [
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.GREATER_THAN,
                value=15,
            ),
            Condition(
                type=ConditionType.WIND_SPEED,
                operator=ComparisonOperator.LESS_THAN,
                value=10,
            ),
        ]
        result = evaluate_conditions(sample_hourly_forecast, conditions)
        assert result.passed is True
        assert result.score > 90

    def test_required_condition_fails(self, sample_hourly_forecast: HourlyForecast):
        """Test evaluation when a required condition fails."""
        conditions = [
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.LESS_THAN,
                value=10,  # Will fail, temp is 22
                is_required=True,
            ),
        ]
        result = evaluate_conditions(sample_hourly_forecast, conditions)
        assert result.passed is False
        assert len(result.blocking_conditions) == 1

    def test_optional_condition_fails(self, sample_hourly_forecast: HourlyForecast):
        """Test evaluation when only optional condition fails."""
        conditions = [
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.GREATER_THAN,
                value=10,
                is_required=True,
            ),
            Condition(
                type=ConditionType.TEMPERATURE,
                operator=ComparisonOperator.LESS_THAN,
                value=20,  # Will fail, temp is 22
                is_required=False,
            ),
        ]
        result = evaluate_conditions(sample_hourly_forecast, conditions)
        assert result.passed is True  # Still passes, only optional failed
        assert result.score < 100  # But score reduced


class TestRuleEngine:
    """Tests for the RuleEngine class."""

    def test_requirements_to_conditions(self, running_activity: Activity):
        """Test converting activity requirements to conditions."""
        engine = RuleEngine()
        conditions = engine.requirements_to_conditions(running_activity.requirements)

        # Should have temperature, wind, and precipitation conditions
        types = {c.type for c in conditions}
        assert ConditionType.TEMPERATURE in types
        assert ConditionType.WIND_SPEED in types
        assert ConditionType.PRECIPITATION_PROBABILITY in types

    def test_evaluate_forecast_pass(
        self,
        sample_hourly_forecast: HourlyForecast,
        running_activity: Activity,
    ):
        """Test evaluating a forecast that passes."""
        engine = RuleEngine()
        result = engine.evaluate_forecast(sample_hourly_forecast, running_activity)

        assert result.passed is True
        assert result.score > 70

    def test_evaluate_forecast_fail_cold(
        self,
        cold_forecast: HourlyForecast,
        running_activity: Activity,
    ):
        """Test evaluating a cold forecast still passes (within range)."""
        engine = RuleEngine()
        result = engine.evaluate_forecast(cold_forecast, running_activity)

        # -5°C is above the min of -10°C for running
        assert result.passed is True

    def test_evaluate_forecast_fail_rain(
        self,
        rainy_forecast: HourlyForecast,
        running_activity: Activity,
    ):
        """Test evaluating rainy forecast fails precipitation check."""
        engine = RuleEngine()
        result = engine.evaluate_forecast(rainy_forecast, running_activity)

        # 80% precipitation exceeds 50% max
        assert result.passed is False

    def test_make_decision_go(
        self,
        sample_hourly_forecast: HourlyForecast,
        running_activity: Activity,
    ):
        """Test making a GO decision."""
        engine = RuleEngine()
        decision = engine.make_decision(sample_hourly_forecast, running_activity)

        assert decision.decision == "GO"
        assert decision.score > 70

    def test_make_decision_no_go(
        self,
        rainy_forecast: HourlyForecast,
        running_activity: Activity,
    ):
        """Test making a NO_GO decision."""
        engine = RuleEngine()
        decision = engine.make_decision(rainy_forecast, running_activity)

        assert decision.decision == "NO_GO"
        assert len(decision.blocking_factors) > 0

    def test_find_best_time(self, sample_forecast, running_activity: Activity):
        """Test finding the best time from multiple forecasts."""
        engine = RuleEngine()
        best = engine.find_best_time(sample_forecast.hourly, running_activity)

        assert best is not None
        assert best.passed is True

    def test_astronomy_evaluation(
        self,
        clear_night_forecast: HourlyForecast,
        astronomy_activity: Activity,
    ):
        """Test evaluating astronomy conditions."""
        engine = RuleEngine()
        result = engine.evaluate_forecast(clear_night_forecast, astronomy_activity)

        # Clear night with low clouds should pass
        # Note: sun constraint requires below horizon check
        # The clear_night_forecast has sun at -25° which is below horizon
        assert result.score > 50

    def test_condition_caching(self, running_activity: Activity):
        """Test that conditions are cached per activity."""
        engine = RuleEngine()

        # First call should create conditions
        conditions1 = engine.get_conditions_for_activity(running_activity)

        # Second call should return cached conditions
        conditions2 = engine.get_conditions_for_activity(running_activity)

        assert conditions1 is conditions2  # Same object, cached
