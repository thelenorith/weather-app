"""Domain models for weather event recommendations."""

from weather_events.models.location import Coordinates, Location
from weather_events.models.weather import (
    WeatherCondition,
    HourlyForecast,
    Forecast,
    CloudCover,
    Precipitation,
    Wind,
    AstronomicalData,
)
from weather_events.models.event import (
    Event,
    EventType,
    EventSource,
    EventTimeAdjustment,
)
from weather_events.models.activity import (
    Activity,
    ActivityCategory,
    ActivityRequirements,
)
from weather_events.models.recommendation import (
    Recommendation,
    RecommendationType,
    GearRecommendation,
    TimeSlotRecommendation,
    GoNoGoDecision,
    DecisionFactor,
    Severity,
)

__all__ = [
    # Location
    "Coordinates",
    "Location",
    # Weather
    "WeatherCondition",
    "HourlyForecast",
    "Forecast",
    "CloudCover",
    "Precipitation",
    "Wind",
    "AstronomicalData",
    # Event
    "Event",
    "EventType",
    "EventSource",
    "EventTimeAdjustment",
    # Activity
    "Activity",
    "ActivityCategory",
    "ActivityRequirements",
    # Recommendation
    "Recommendation",
    "RecommendationType",
    "GearRecommendation",
    "TimeSlotRecommendation",
    "GoNoGoDecision",
    "DecisionFactor",
    "Severity",
]
