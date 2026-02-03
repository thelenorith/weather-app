"""Recommendation systems for weather-based activity planning."""

from weather_events.recommendations.gear import (
    GearRule,
    GearRecommender,
    create_running_gear_rules,
    create_cycling_gear_rules,
)
from weather_events.recommendations.time_slots import (
    TimeSlotFinder,
    find_optimal_slots,
)
from weather_events.recommendations.go_no_go import (
    GoNoGoEvaluator,
    AstronomyGoNoGoEvaluator,
)

__all__ = [
    "GearRule",
    "GearRecommender",
    "create_running_gear_rules",
    "create_cycling_gear_rules",
    "TimeSlotFinder",
    "find_optimal_slots",
    "GoNoGoEvaluator",
    "AstronomyGoNoGoEvaluator",
]
