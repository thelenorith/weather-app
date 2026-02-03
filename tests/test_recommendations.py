"""Tests for the recommendations module."""

from datetime import datetime, timedelta, timezone

import pytest

from weather_events.models.recommendation import GearItem
from weather_events.models.weather import (
    AstronomicalData,
    CloudCover,
    HourlyForecast,
    Precipitation,
    WeatherCondition,
    Wind,
)
from weather_events.recommendations.gear import (
    GearRecommender,
    GearRule,
    create_cycling_gear_rules,
    create_running_gear_rules,
)
from weather_events.recommendations.go_no_go import (
    AstronomyGoNoGoEvaluator,
    GoNoGoEvaluator,
    SolarObservingEvaluator,
    WeightedFactor,
    DecisionWeight,
)
from weather_events.recommendations.time_slots import TimeSlotFinder


class TestGearRule:
    """Tests for GearRule."""

    def test_basic_rule_matches(self, sample_hourly_forecast: HourlyForecast):
        """Test basic rule matching."""
        rule = GearRule(
            item=GearItem(name="T-Shirt", category="torso_base"),
            min_temp_c=15,
            max_temp_c=30,
        )
        # Forecast is 22°C, should match
        assert rule.matches(sample_hourly_forecast) is True

    def test_rule_temperature_too_cold(self, cold_forecast: HourlyForecast):
        """Test rule doesn't match when too cold."""
        rule = GearRule(
            item=GearItem(name="Tank Top", category="torso_base"),
            min_temp_c=25,
        )
        # Forecast is -5°C, should not match
        assert rule.matches(cold_forecast) is False

    def test_rule_temperature_too_hot(self, sample_hourly_forecast: HourlyForecast):
        """Test rule doesn't match when too hot."""
        rule = GearRule(
            item=GearItem(name="Heavy Jacket", category="torso_outer"),
            max_temp_c=10,
        )
        # Forecast is 22°C, should not match
        assert rule.matches(sample_hourly_forecast) is False

    def test_rule_wind_requirement(self, sample_hourly_forecast: HourlyForecast):
        """Test rule with wind requirement."""
        rule = GearRule(
            item=GearItem(name="Wind Jacket", category="torso_outer"),
            min_wind_ms=5,
        )
        # Forecast wind is 3.5 m/s, should not match
        assert rule.matches(sample_hourly_forecast) is False

        # Create windier forecast
        windy = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=22.0,
            wind=Wind(speed_ms=8.0),
        )
        assert rule.matches(windy) is True

    def test_rule_rain_requirement(self, rainy_forecast: HourlyForecast):
        """Test rule requiring rain."""
        rule = GearRule(
            item=GearItem(name="Rain Jacket", category="torso_outer"),
            requires_rain=True,
        )
        assert rule.matches(rainy_forecast) is True

    def test_rule_rain_requirement_dry(self, sample_hourly_forecast: HourlyForecast):
        """Test rain rule doesn't match in dry conditions."""
        rule = GearRule(
            item=GearItem(name="Rain Jacket", category="torso_outer"),
            requires_rain=True,
        )
        assert rule.matches(sample_hourly_forecast) is False


class TestGearRecommender:
    """Tests for GearRecommender."""

    def test_basic_recommendation(self, sample_hourly_forecast: HourlyForecast):
        """Test basic gear recommendation."""
        rules = [
            GearRule(
                item=GearItem(name="T-Shirt", category="torso_base"),
                min_temp_c=15,
                max_temp_c=30,
                priority=2,
            ),
            GearRule(
                item=GearItem(name="Shorts", category="legs"),
                min_temp_c=15,
                priority=1,
            ),
        ]
        recommender = GearRecommender(rules=rules, activity="running")
        recommendation = recommender.recommend(sample_hourly_forecast)

        assert len(recommendation.items) == 2
        assert recommendation.activity == "running"
        assert recommendation.temperature_c == 22.0

    def test_exclusive_rules(self, cold_forecast: HourlyForecast):
        """Test exclusive rules only select one per category."""
        rules = [
            GearRule(
                item=GearItem(name="T-Shirt", category="torso_base"),
                min_temp_c=15,
                priority=1,
                exclusive=True,
            ),
            GearRule(
                item=GearItem(name="Long Sleeve", category="torso_base"),
                max_temp_c=10,
                priority=2,
                exclusive=True,
            ),
            GearRule(
                item=GearItem(name="Thermal", category="torso_base"),
                max_temp_c=0,
                priority=3,
                exclusive=True,
            ),
        ]
        recommender = GearRecommender(rules=rules)
        recommendation = recommender.recommend(cold_forecast)

        # Should only have thermal (coldest option that matches -5°C)
        torso_items = [i for i in recommendation.items if i.category == "torso_base"]
        assert len(torso_items) == 1
        assert torso_items[0].name == "Long Sleeve"

    def test_running_gear_rules_warm(self, sample_hourly_forecast: HourlyForecast):
        """Test running gear recommendations for warm weather."""
        rules = create_running_gear_rules()
        recommender = GearRecommender(rules=rules, activity="running")
        recommendation = recommender.recommend(sample_hourly_forecast)

        # At 22°C, should recommend shorts and t-shirt type items
        item_names = [i.name for i in recommendation.items]
        assert any("Shirt" in name or "Singlet" in name for name in item_names)

    def test_running_gear_rules_cold(self, cold_forecast: HourlyForecast):
        """Test running gear recommendations for cold weather."""
        rules = create_running_gear_rules()
        recommender = GearRecommender(rules=rules, activity="running")
        recommendation = recommender.recommend(cold_forecast)

        # At -5°C, should recommend warm items
        item_names = [i.name for i in recommendation.items]
        assert any("Thermal" in name or "Beanie" in name for name in item_names)
        assert any("Gloves" in name for name in item_names)

    def test_cycling_gear_rules(self, sample_hourly_forecast: HourlyForecast):
        """Test cycling gear recommendations."""
        rules = create_cycling_gear_rules()
        recommender = GearRecommender(rules=rules, activity="cycling")
        recommendation = recommender.recommend(sample_hourly_forecast)

        # Should have cycling-specific items
        assert recommendation.activity == "cycling"
        assert len(recommendation.items) > 0


class TestGoNoGoEvaluator:
    """Tests for GoNoGoEvaluator."""

    def test_weighted_factor_evaluation(self):
        """Test weighted factor evaluation."""
        factor = WeightedFactor(
            name="temperature",
            display_name="Temperature",
            weight=DecisionWeight.MEDIUM,
            threshold=30,
            threshold_type="max",
        )

        passed, severity = factor.evaluate(25)
        assert passed is True

        passed, severity = factor.evaluate(35)
        assert passed is False

    def test_weighted_factor_min_threshold(self):
        """Test weighted factor with minimum threshold."""
        factor = WeightedFactor(
            name="temperature",
            display_name="Temperature",
            weight=DecisionWeight.MEDIUM,
            threshold=10,
            threshold_type="min",
        )

        passed, _ = factor.evaluate(15)
        assert passed is True

        passed, _ = factor.evaluate(5)
        assert passed is False

    def test_weighted_factor_blocking(self):
        """Test blocking factor evaluation."""
        factor = WeightedFactor(
            name="cloud_cover",
            display_name="Cloud Cover",
            weight=DecisionWeight.CRITICAL,
            threshold=30,
            threshold_type="max",
            is_blocking=True,
        )

        _, severity = factor.evaluate(50)
        from weather_events.models.recommendation import Severity

        assert severity == Severity.CRITICAL

    def test_evaluator_go_decision(self, sample_hourly_forecast: HourlyForecast):
        """Test evaluator makes GO decision for good conditions."""
        factors = [
            WeightedFactor(
                name="cloud_cover",
                display_name="Cloud Cover",
                weight=DecisionWeight.HIGH,
                threshold=60,
                threshold_type="max",
            ),
            WeightedFactor(
                name="wind_speed",
                display_name="Wind",
                weight=DecisionWeight.MEDIUM,
                threshold=10,
                threshold_type="max",
            ),
        ]
        evaluator = GoNoGoEvaluator(factors)
        decision = evaluator.evaluate(sample_hourly_forecast)

        assert decision.decision == "GO"

    def test_evaluator_no_go_decision(self, rainy_forecast: HourlyForecast):
        """Test evaluator makes NO_GO decision for bad conditions."""
        factors = [
            WeightedFactor(
                name="precipitation_probability",
                display_name="Rain Chance",
                weight=DecisionWeight.CRITICAL,
                threshold=30,
                threshold_type="max",
                is_blocking=True,
            ),
        ]
        evaluator = GoNoGoEvaluator(factors)
        decision = evaluator.evaluate(rainy_forecast)

        assert decision.decision == "NO_GO"
        assert "Rain Chance" in decision.blocking_factors


class TestAstronomyGoNoGoEvaluator:
    """Tests for astronomy-specific go/no-go evaluator."""

    def test_clear_night_go(self, clear_night_forecast: HourlyForecast):
        """Test GO decision for clear night."""
        evaluator = AstronomyGoNoGoEvaluator(
            max_cloud_cover=30,
            max_precipitation_prob=20,
            max_wind_speed=8,
        )
        decision = evaluator.evaluate(clear_night_forecast)

        # Clear night with 5% clouds should be GO
        assert decision.decision == "GO"

    def test_cloudy_night_no_go(self):
        """Test NO_GO decision for cloudy night."""
        cloudy_night = HourlyForecast(
            time=datetime(2024, 6, 15, 23, 0, tzinfo=timezone.utc),
            temperature_c=18.0,
            cloud_cover=CloudCover(total_percent=70),
            precipitation=Precipitation(probability_percent=5),
            wind=Wind(speed_ms=3.0),
        )

        evaluator = AstronomyGoNoGoEvaluator(max_cloud_cover=30)
        decision = evaluator.evaluate(cloudy_night)

        assert decision.decision == "NO_GO"
        assert "Cloud Cover" in decision.blocking_factors

    def test_custom_thresholds(self, clear_night_forecast: HourlyForecast):
        """Test evaluator with custom thresholds."""
        # Very strict cloud threshold
        evaluator = AstronomyGoNoGoEvaluator(max_cloud_cover=3)
        decision = evaluator.evaluate(clear_night_forecast)

        # 5% clouds exceeds 3% threshold
        assert decision.decision == "NO_GO"


class TestSolarObservingEvaluator:
    """Tests for solar observation evaluator."""

    def test_good_solar_conditions(self):
        """Test GO decision for good solar observing conditions."""
        solar_forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
            temperature_c=25.0,
            cloud_cover=CloudCover(total_percent=5),
            wind=Wind(speed_ms=2.0),
            astronomical=AstronomicalData(sun_altitude_deg=45),
        )

        evaluator = SolarObservingEvaluator(
            max_cloud_cover=15,
            min_sun_altitude=20,
            max_wind_speed=5,
        )
        decision = evaluator.evaluate(solar_forecast)

        assert decision.decision == "GO"

    def test_sun_too_low(self):
        """Test NO_GO when sun is too low."""
        low_sun_forecast = HourlyForecast(
            time=datetime(2024, 6, 15, 7, 0, tzinfo=timezone.utc),
            temperature_c=20.0,
            cloud_cover=CloudCover(total_percent=5),
            wind=Wind(speed_ms=2.0),
            astronomical=AstronomicalData(sun_altitude_deg=10),
        )

        evaluator = SolarObservingEvaluator(min_sun_altitude=20)
        decision = evaluator.evaluate(low_sun_forecast)

        assert decision.decision == "NO_GO"
        assert "Sun Altitude" in decision.blocking_factors


class TestTimeSlotFinder:
    """Tests for TimeSlotFinder."""

    def test_find_slots_basic(self, sample_forecast, running_activity):
        """Test finding time slots in a forecast."""
        finder = TimeSlotFinder()
        recommendation = finder.find_slots(
            forecast=sample_forecast,
            activity=running_activity,
            min_duration=timedelta(hours=1),
        )

        assert not recommendation.no_suitable_slots
        assert len(recommendation.slots) > 0

    def test_find_optimal_slot(self, sample_forecast, running_activity):
        """Test finding the optimal slot."""
        finder = TimeSlotFinder()
        recommendation = finder.find_slots(
            forecast=sample_forecast,
            activity=running_activity,
            min_duration=timedelta(hours=1),
            max_slots=3,
        )

        assert recommendation.optimal_slot is not None
        assert recommendation.optimal_slot.is_optimal is True

    def test_no_suitable_slots(self, sample_forecast, astronomy_activity):
        """Test when no suitable slots are found."""
        # Astronomy requires night, but our sample forecast is daytime
        finder = TimeSlotFinder()
        recommendation = finder.find_slots(
            forecast=sample_forecast,
            activity=astronomy_activity,
            min_duration=timedelta(hours=1),
        )

        # Should fail because daytime forecast doesn't meet astronomy requirements
        # (sun below horizon required)
        assert recommendation.no_suitable_slots is True

    def test_slot_scoring(self, sample_forecast, running_activity):
        """Test that slots are properly scored and ranked."""
        finder = TimeSlotFinder()
        recommendation = finder.find_slots(
            forecast=sample_forecast,
            activity=running_activity,
            min_duration=timedelta(hours=1),
            max_slots=5,
        )

        if len(recommendation.slots) > 1:
            # Slots should be sorted by score descending
            scores = [s.score for s in recommendation.slots]
            assert scores == sorted(scores, reverse=True)

    def test_slot_duration_requirements(self, sample_forecast, running_activity):
        """Test minimum duration requirements."""
        finder = TimeSlotFinder()

        # Request 2-hour minimum
        recommendation = finder.find_slots(
            forecast=sample_forecast,
            activity=running_activity,
            min_duration=timedelta(hours=2),
        )

        for slot in recommendation.slots:
            assert slot.duration >= timedelta(hours=2)
