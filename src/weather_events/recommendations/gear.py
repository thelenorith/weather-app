"""Gear and clothing recommendation system.

This module provides a rule-based system for recommending clothing and gear
based on weather conditions. Rules can be personalized per user to account
for individual preferences (e.g., some people get cold hands earlier).

## How Rules Work

Each GearRule defines:
- What gear item to recommend
- What conditions trigger the recommendation
- Priority (for ordering recommendations)

Rules are evaluated in priority order, and the first matching rule for each
category (tops, bottoms, accessories, etc.) wins. Multiple rules can match
for accessories (e.g., both gloves AND hat can be recommended).

## Personalization

Users can customize rules by:
- Adjusting temperature thresholds (some people run warm/cold)
- Adding/removing gear items
- Changing priorities
- Creating entirely custom rules

Example:
    ```python
    # Create a custom rule for gloves at a warmer temperature
    # (for someone whose hands get cold easily)
    cold_hands_gloves = GearRule(
        item=GearItem(name="Light Gloves", category="accessories"),
        min_temp_c=None,
        max_temp_c=10,  # Gloves at 10°C instead of default 5°C
        priority=3,
    )
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from weather_events.models.recommendation import GearItem, GearRecommendation
from weather_events.models.weather import HourlyForecast


class GearCategory(str, Enum):
    """Categories of gear for organization."""

    HEAD = "head"
    FACE = "face"
    TORSO_BASE = "torso_base"  # Base layer
    TORSO_MID = "torso_mid"  # Mid layer
    TORSO_OUTER = "torso_outer"  # Outer layer
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    ACCESSORIES = "accessories"
    SAFETY = "safety"


@dataclass
class GearRule:
    """A rule for recommending a piece of gear based on conditions.

    Rules specify temperature ranges, precipitation conditions, and other
    factors that trigger the gear recommendation.

    Attributes:
        item: The gear item to recommend
        min_temp_c: Minimum temperature (inclusive) to recommend this item
        max_temp_c: Maximum temperature (inclusive) to recommend this item
        min_wind_ms: Minimum wind speed to trigger this recommendation
        max_precipitation_percent: Only recommend if precipitation below this
        requires_rain: Only recommend if rain is expected
        requires_night: Only recommend during night
        priority: Lower priority = recommended first (for exclusive categories)
        exclusive: If True, only one item from this rule's category is used
        description: Human-readable description of when this is recommended
    """

    item: GearItem
    min_temp_c: float | None = None
    max_temp_c: float | None = None
    min_feels_like_c: float | None = None
    max_feels_like_c: float | None = None
    min_wind_ms: float | None = None
    max_precipitation_percent: float | None = None
    requires_rain: bool = False
    requires_night: bool = False
    priority: int = 5
    exclusive: bool = True
    description: str | None = None

    def matches(self, forecast: HourlyForecast) -> bool:
        """Check if this rule matches the given forecast conditions.

        Args:
            forecast: Weather forecast to check against

        Returns:
            True if conditions match this rule
        """
        # Temperature checks
        temp = forecast.temperature_c
        if self.min_temp_c is not None and temp < self.min_temp_c:
            return False
        if self.max_temp_c is not None and temp > self.max_temp_c:
            return False

        # Feels-like temperature checks
        feels_like = forecast.feels_like_c or temp
        if self.min_feels_like_c is not None and feels_like < self.min_feels_like_c:
            return False
        if self.max_feels_like_c is not None and feels_like > self.max_feels_like_c:
            return False

        # Wind check
        if self.min_wind_ms is not None:
            wind_speed = forecast.wind.speed_ms if forecast.wind else 0
            if wind_speed < self.min_wind_ms:
                return False

        # Precipitation check
        precip_prob = 0.0
        if forecast.precipitation:
            precip_prob = forecast.precipitation.probability_percent

        if self.max_precipitation_percent is not None:
            if precip_prob > self.max_precipitation_percent:
                return False

        if self.requires_rain and precip_prob < 30:
            return False

        # Night check
        if self.requires_night:
            if forecast.astronomical:
                is_night = forecast.astronomical.is_night()
                if is_night is False:
                    return False

        return True


@dataclass
class GearRecommender:
    """Recommender for gear based on weather conditions.

    This class holds a set of rules and applies them to generate
    gear recommendations.

    Example:
        ```python
        recommender = GearRecommender(rules=create_running_gear_rules())
        recommendation = recommender.recommend(forecast, activity="running")
        for item in recommendation.items:
            print(f"- {item.name} ({item.category})")
        ```
    """

    rules: list[GearRule] = field(default_factory=list)
    activity: str = "general"

    def recommend(
        self,
        forecast: HourlyForecast,
        activity: str | None = None,
    ) -> GearRecommendation:
        """Generate gear recommendations for the given conditions.

        Args:
            forecast: Weather forecast to base recommendations on
            activity: Activity name (for display)

        Returns:
            GearRecommendation with recommended items
        """
        activity_name = activity or self.activity

        # Find matching rules
        matching_rules = [r for r in self.rules if r.matches(forecast)]

        # Sort by priority (lower = first)
        matching_rules.sort(key=lambda r: r.priority)

        # Apply exclusivity rules
        items: list[GearItem] = []
        used_categories: set[str] = set()

        for rule in matching_rules:
            category = rule.item.category

            # For exclusive rules, only use first match per category
            if rule.exclusive and category in used_categories:
                continue

            items.append(rule.item)
            used_categories.add(category)

        # Build the recommendation
        recommendation = GearRecommendation(
            activity=activity_name,
            conditions_summary=_build_conditions_summary(forecast),
            items=items,
            temperature_c=forecast.temperature_c,
            feels_like_c=forecast.feels_like_c,
            wind_speed_ms=forecast.wind.speed_ms if forecast.wind else None,
            precipitation_percent=(
                forecast.precipitation.probability_percent
                if forecast.precipitation
                else None
            ),
        )

        # Organize by category
        for item in items:
            recommendation.add_item(item)

        # Add notes based on conditions
        if forecast.precipitation and forecast.precipitation.probability_percent > 50:
            recommendation.notes.append("High chance of rain - waterproof gear recommended")

        if forecast.wind and forecast.wind.speed_ms > 8:
            recommendation.notes.append("Windy conditions - wind-resistant layers helpful")

        if forecast.uv_index and forecast.uv_index > 6:
            recommendation.notes.append("High UV - sun protection recommended")

        return recommendation


def _build_conditions_summary(forecast: HourlyForecast) -> str:
    """Build a human-readable summary of conditions."""
    parts = []

    # Temperature
    temp_f = forecast.temperature_f
    parts.append(f"{forecast.temperature_c:.0f}°C ({temp_f:.0f}°F)")

    # Feels like
    if forecast.feels_like_c and abs(forecast.feels_like_c - forecast.temperature_c) > 2:
        feels_f = forecast.feels_like_f
        parts.append(f"feels like {forecast.feels_like_c:.0f}°C ({feels_f:.0f}°F)")

    # Wind
    if forecast.wind:
        parts.append(f"wind {forecast.wind.speed_ms:.0f} m/s")

    # Precipitation
    if forecast.precipitation and forecast.precipitation.probability_percent > 10:
        parts.append(f"{forecast.precipitation.probability_percent:.0f}% chance of rain")

    return ", ".join(parts)


def create_running_gear_rules() -> list[GearRule]:
    """Create default gear rules for running.

    These rules are based on typical running in temperate climates.
    Users should customize based on their personal preferences.

    Temperature ranges (approximate):
    - Hot (>25°C): Minimal clothing
    - Warm (20-25°C): Shorts, singlet
    - Mild (15-20°C): Shorts, t-shirt
    - Cool (10-15°C): Shorts or tights, long sleeve
    - Cold (5-10°C): Tights, long sleeve, light jacket
    - Very cold (0-5°C): Tights, layers, gloves, hat
    - Freezing (<0°C): Full layers, thermal gear
    """
    rules = []

    # HEAD
    rules.append(
        GearRule(
            item=GearItem(name="Running Cap", category="head", priority=3),
            min_temp_c=15,
            description="Cap for sun protection or light warmth",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Beanie", category="head", priority=2),
            max_temp_c=5,
            description="Warm hat for cold conditions",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Headband/Ear Warmer", category="head", priority=2),
            min_temp_c=0,
            max_temp_c=10,
            description="Ear coverage without full hat",
            priority=2,
        )
    )

    # TORSO - Base layer
    rules.append(
        GearRule(
            item=GearItem(name="Singlet/Tank", category="torso_base", priority=1),
            min_temp_c=22,
            description="Hot weather minimal top",
            priority=1,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="T-Shirt", category="torso_base", priority=2),
            min_temp_c=12,
            max_temp_c=22,
            description="Standard running shirt",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Long Sleeve", category="torso_base", priority=3),
            min_temp_c=5,
            max_temp_c=15,
            description="Long sleeve for cooler weather",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Thermal Base Layer", category="torso_base", priority=4),
            max_temp_c=5,
            description="Warm base layer for cold",
            priority=4,
        )
    )

    # TORSO - Mid/Outer layer
    rules.append(
        GearRule(
            item=GearItem(name="Light Jacket/Vest", category="torso_outer", priority=3),
            max_temp_c=10,
            exclusive=True,
            description="Light layer for cool conditions",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Wind Jacket", category="torso_outer", priority=2),
            max_temp_c=12,
            min_wind_ms=6,
            exclusive=True,
            description="Wind protection",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Rain Jacket", category="torso_outer", priority=1),
            requires_rain=True,
            exclusive=True,
            description="Rain protection",
            priority=1,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Insulated Jacket", category="torso_outer", priority=4),
            max_temp_c=0,
            exclusive=True,
            description="Heavy warmth for freezing conditions",
            priority=4,
        )
    )

    # HANDS - Note: These are NOT exclusive, allowing for layered gloves
    rules.append(
        GearRule(
            item=GearItem(name="Light Gloves", category="hands", priority=3),
            max_temp_c=8,
            min_temp_c=0,
            exclusive=True,
            description="Light hand coverage",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Warm Gloves", category="hands", priority=2),
            max_temp_c=0,
            exclusive=True,
            description="Warm hand coverage for cold",
            priority=2,
        )
    )

    # LEGS
    rules.append(
        GearRule(
            item=GearItem(name="Shorts", category="legs", priority=1),
            min_temp_c=12,
            description="Standard running shorts",
            priority=1,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="3/4 Tights", category="legs", priority=2),
            min_temp_c=5,
            max_temp_c=15,
            description="Knee-length tights",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Full Tights", category="legs", priority=3),
            max_temp_c=10,
            description="Full-length tights",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Thermal Tights", category="legs", priority=4),
            max_temp_c=0,
            description="Insulated tights for freezing",
            priority=4,
        )
    )

    # ACCESSORIES
    rules.append(
        GearRule(
            item=GearItem(name="Sunglasses", category="accessories", priority=2),
            min_temp_c=10,
            max_precipitation_percent=30,
            exclusive=False,
            description="Eye protection in dry weather",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Reflective Vest", category="safety", priority=1),
            requires_night=True,
            exclusive=False,
            description="Visibility at night",
            priority=1,
        )
    )

    return rules


def create_cycling_gear_rules() -> list[GearRule]:
    """Create default gear rules for cycling.

    Cycling generally requires more wind protection than running due to
    wind chill from speed. These rules account for that.
    """
    rules = []

    # HEAD
    rules.append(
        GearRule(
            item=GearItem(name="Cycling Cap", category="head", priority=3),
            min_temp_c=15,
            description="Cap under helmet",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Thermal Skull Cap", category="head", priority=2),
            max_temp_c=10,
            description="Warm cap under helmet",
            priority=2,
        )
    )

    # TORSO
    rules.append(
        GearRule(
            item=GearItem(name="Jersey", category="torso_base", priority=2),
            min_temp_c=15,
            description="Standard cycling jersey",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Long Sleeve Jersey", category="torso_base", priority=3),
            min_temp_c=8,
            max_temp_c=18,
            description="Long sleeve for cooler rides",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Thermal Base Layer", category="torso_base", priority=4),
            max_temp_c=10,
            description="Warm base layer",
            priority=4,
        )
    )

    # Outer layers
    rules.append(
        GearRule(
            item=GearItem(name="Gilet/Vest", category="torso_outer", priority=3),
            max_temp_c=15,
            exclusive=True,
            description="Core warmth, arm mobility",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Wind Jacket", category="torso_outer", priority=2),
            max_temp_c=12,
            min_wind_ms=4,
            exclusive=True,
            description="Wind protection",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Rain Jacket", category="torso_outer", priority=1),
            requires_rain=True,
            exclusive=True,
            description="Waterproof layer",
            priority=1,
        )
    )

    # HANDS
    rules.append(
        GearRule(
            item=GearItem(name="Short Finger Gloves", category="hands", priority=4),
            min_temp_c=15,
            description="Grip and padding",
            priority=4,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Full Finger Gloves", category="hands", priority=3),
            min_temp_c=8,
            max_temp_c=18,
            description="Full hand coverage",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Winter Gloves", category="hands", priority=2),
            max_temp_c=10,
            description="Insulated gloves",
            priority=2,
        )
    )

    # LEGS
    rules.append(
        GearRule(
            item=GearItem(name="Bib Shorts", category="legs", priority=1),
            min_temp_c=18,
            description="Standard cycling shorts",
            priority=1,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Knee Warmers", category="legs", priority=2),
            min_temp_c=12,
            max_temp_c=20,
            exclusive=False,
            description="Knee protection",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Bib Tights", category="legs", priority=3),
            max_temp_c=15,
            description="Full leg coverage",
            priority=3,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Thermal Tights", category="legs", priority=4),
            max_temp_c=5,
            description="Insulated tights",
            priority=4,
        )
    )

    # FEET
    rules.append(
        GearRule(
            item=GearItem(name="Shoe Covers", category="feet", priority=2),
            max_temp_c=10,
            exclusive=False,
            description="Toe warmth",
            priority=2,
        )
    )
    rules.append(
        GearRule(
            item=GearItem(name="Waterproof Shoe Covers", category="feet", priority=1),
            requires_rain=True,
            exclusive=False,
            description="Dry feet in rain",
            priority=1,
        )
    )

    # SAFETY
    rules.append(
        GearRule(
            item=GearItem(name="Front & Rear Lights", category="safety", priority=1),
            requires_night=True,
            exclusive=False,
            description="Visibility at night",
            priority=1,
        )
    )

    return rules
