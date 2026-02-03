"""Recommendation models for weather-based decisions."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    """Types of recommendations the system can provide."""

    GEAR = "gear"  # Clothing/equipment recommendations
    TIME_SLOT = "time_slot"  # Optimal time window
    GO_NO_GO = "go_no_go"  # Go/no-go decision
    FORECAST = "forecast"  # Weather forecast summary
    WARNING = "warning"  # Weather warning/alert
    INFO = "info"  # General information


class Severity(str, Enum):
    """Severity level for recommendations and decisions."""

    INFO = "info"
    GOOD = "good"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"


class DecisionFactor(BaseModel):
    """A single factor contributing to a go/no-go decision."""

    name: str = Field(..., description="Factor name (e.g., 'cloud_cover', 'wind')")
    display_name: str = Field(..., description="Human-readable name")
    value: float | str = Field(..., description="Current value of this factor")
    unit: str | None = Field(default=None, description="Unit of measurement")
    threshold: float | str | None = Field(
        default=None, description="Threshold for this factor"
    )
    is_acceptable: bool = Field(
        ..., description="Whether this factor meets requirements"
    )
    is_ideal: bool = Field(
        default=False, description="Whether this factor is in ideal range"
    )
    weight: float = Field(
        default=1.0, ge=0, le=10, description="Weight of this factor in scoring"
    )
    severity: Severity = Field(
        default=Severity.INFO, description="Severity if not acceptable"
    )
    notes: str | None = Field(default=None, description="Additional notes")


class GoNoGoDecision(BaseModel):
    """A go/no-go decision for an activity."""

    decision: str = Field(..., description="GO, NO_GO, or MARGINAL")
    confidence: float = Field(
        ..., ge=0, le=1, description="Confidence in the decision (0-1)"
    )
    score: float = Field(
        ..., ge=0, le=100, description="Overall suitability score (0-100)"
    )

    # Factors that went into the decision
    factors: list[DecisionFactor] = Field(
        default_factory=list, description="Individual factors evaluated"
    )

    # Blocking factors (any of these makes it NO_GO)
    blocking_factors: list[str] = Field(
        default_factory=list, description="Factors that block the activity"
    )

    # Summary
    summary: str = Field(..., description="Human-readable summary of the decision")
    recommendations: list[str] = Field(
        default_factory=list, description="Specific recommendations"
    )

    # Timing
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When decision was made"
    )
    valid_for: datetime | None = Field(
        default=None, description="Time this decision applies to"
    )

    def is_go(self) -> bool:
        """Check if decision is GO."""
        return self.decision == "GO"

    def is_no_go(self) -> bool:
        """Check if decision is NO_GO."""
        return self.decision == "NO_GO"

    def is_marginal(self) -> bool:
        """Check if decision is MARGINAL."""
        return self.decision == "MARGINAL"


class GearItem(BaseModel):
    """A single piece of gear or clothing."""

    name: str = Field(..., description="Gear item name")
    category: str = Field(..., description="Category (e.g., 'top', 'bottom', 'accessories')")
    description: str | None = Field(default=None, description="Description or notes")
    priority: int = Field(
        default=1, ge=1, le=10, description="Priority (1=essential, 10=optional)"
    )
    conditions: list[str] = Field(
        default_factory=list, description="Conditions that trigger this item"
    )


class GearRecommendation(BaseModel):
    """Gear/clothing recommendations based on conditions."""

    activity: str = Field(..., description="Activity this recommendation is for")
    conditions_summary: str = Field(
        ..., description="Summary of weather conditions"
    )

    # Recommended items by category
    items: list[GearItem] = Field(
        default_factory=list, description="Recommended gear items"
    )

    # Organized by category for easy display
    by_category: dict[str, list[GearItem]] = Field(
        default_factory=dict, description="Items organized by category"
    )

    # Weather context
    temperature_c: float | None = Field(default=None, description="Temperature")
    feels_like_c: float | None = Field(default=None, description="Feels-like temperature")
    wind_speed_ms: float | None = Field(default=None, description="Wind speed")
    precipitation_percent: float | None = Field(
        default=None, description="Precipitation probability"
    )

    # Notes
    notes: list[str] = Field(
        default_factory=list, description="Additional notes or warnings"
    )

    def add_item(self, item: GearItem) -> None:
        """Add a gear item and update category index."""
        self.items.append(item)
        if item.category not in self.by_category:
            self.by_category[item.category] = []
        self.by_category[item.category].append(item)


class TimeSlot(BaseModel):
    """A potential time slot for an activity."""

    start: datetime = Field(..., description="Slot start time")
    end: datetime = Field(..., description="Slot end time")
    score: float = Field(
        ..., ge=0, le=100, description="Suitability score (0-100)"
    )
    is_optimal: bool = Field(
        default=False, description="Whether this is the optimal slot"
    )

    # Weather summary for this slot
    avg_temperature_c: float | None = Field(default=None)
    avg_cloud_cover_percent: float | None = Field(default=None)
    max_precipitation_percent: float | None = Field(default=None)
    avg_wind_speed_ms: float | None = Field(default=None)

    # Reasons this slot was scored as it was
    advantages: list[str] = Field(
        default_factory=list, description="Positive factors"
    )
    disadvantages: list[str] = Field(
        default_factory=list, description="Negative factors"
    )

    @property
    def duration(self) -> timedelta:
        """Get slot duration."""
        return self.end - self.start


class TimeSlotRecommendation(BaseModel):
    """Recommendation for optimal time slots for an activity."""

    activity: str = Field(..., description="Activity this recommendation is for")
    search_start: datetime = Field(..., description="Start of search window")
    search_end: datetime = Field(..., description="End of search window")

    # Found slots
    slots: list[TimeSlot] = Field(
        default_factory=list, description="Potential time slots, best first"
    )

    # Best slot (convenience)
    optimal_slot: TimeSlot | None = Field(
        default=None, description="The single best slot found"
    )

    # If no good slots found
    no_suitable_slots: bool = Field(
        default=False, description="True if no suitable slots were found"
    )
    no_slots_reason: str | None = Field(
        default=None, description="Why no suitable slots were found"
    )

    # Metadata
    min_duration_required: timedelta | None = Field(
        default=None, description="Minimum duration that was required"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When recommendation was generated"
    )


class Recommendation(BaseModel):
    """A general recommendation from the system."""

    type: RecommendationType = Field(..., description="Type of recommendation")
    severity: Severity = Field(
        default=Severity.INFO, description="Severity level"
    )
    title: str = Field(..., description="Short title")
    message: str = Field(..., description="Full recommendation message")

    # Optional structured data
    go_no_go: GoNoGoDecision | None = Field(default=None)
    gear: GearRecommendation | None = Field(default=None)
    time_slots: TimeSlotRecommendation | None = Field(default=None)

    # Context
    activity: str | None = Field(
        default=None, description="Activity this applies to"
    )
    event_id: str | None = Field(
        default=None, description="Event this applies to"
    )
    valid_from: datetime | None = Field(default=None)
    valid_until: datetime | None = Field(default=None)

    # Metadata
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When recommendation was generated"
    )
    source: str | None = Field(
        default=None, description="Source of this recommendation"
    )
    raw_data: dict[str, Any] | None = Field(
        default=None, description="Raw data used to generate recommendation"
    )
