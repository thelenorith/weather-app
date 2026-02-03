"""Time slot finder for optimal weather windows.

This module helps find the best time slots for activities based on weather
conditions. It can:
- Find contiguous periods that meet requirements
- Score and rank multiple potential time slots
- Handle minimum duration requirements
- Consider astronomical constraints (for solar/astronomy activities)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from weather_events.models.activity import Activity
from weather_events.models.recommendation import TimeSlot, TimeSlotRecommendation
from weather_events.models.weather import Forecast, HourlyForecast
from weather_events.rules.engine import EvaluationResult, RuleEngine


@dataclass
class SlotCandidate:
    """A candidate time slot being evaluated."""

    start_idx: int
    end_idx: int
    forecasts: list[HourlyForecast]
    results: list[EvaluationResult]

    @property
    def start_time(self) -> datetime:
        return self.forecasts[0].time

    @property
    def end_time(self) -> datetime:
        # End time is start of last hour + 1 hour
        return self.forecasts[-1].time + timedelta(hours=1)

    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def min_score(self) -> float:
        if not self.results:
            return 0
        return min(r.score for r in self.results)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


class TimeSlotFinder:
    """Finds optimal time slots for activities based on weather.

    Example:
        ```python
        finder = TimeSlotFinder(engine=RuleEngine())

        # Find best 1-hour slot for solar observation
        recommendation = finder.find_slots(
            forecast=forecast,
            activity=solar_activity,
            min_duration=timedelta(minutes=30),
            preferred_duration=timedelta(hours=1),
        )

        if recommendation.optimal_slot:
            print(f"Best time: {recommendation.optimal_slot.start}")
        ```
    """

    def __init__(self, engine: RuleEngine | None = None):
        """Initialize the finder.

        Args:
            engine: RuleEngine to use for evaluating conditions
        """
        self.engine = engine or RuleEngine()

    def find_slots(
        self,
        forecast: Forecast,
        activity: Activity,
        min_duration: timedelta = timedelta(minutes=30),
        preferred_duration: timedelta = timedelta(hours=1),
        max_slots: int = 5,
        require_passing: bool = True,
    ) -> TimeSlotRecommendation:
        """Find optimal time slots within a forecast.

        Args:
            forecast: Weather forecast to search within
            activity: Activity with requirements
            min_duration: Minimum acceptable slot duration
            preferred_duration: Preferred slot duration
            max_slots: Maximum number of slots to return
            require_passing: Only return slots that pass all requirements

        Returns:
            TimeSlotRecommendation with ranked slots
        """
        if not forecast.hourly:
            return TimeSlotRecommendation(
                activity=activity.name,
                search_start=datetime.now(),
                search_end=datetime.now(),
                no_suitable_slots=True,
                no_slots_reason="No forecast data available",
            )

        # Evaluate each hour
        results = self.engine.evaluate_forecasts(forecast.hourly, activity)

        # Find contiguous passing periods
        candidates = self._find_contiguous_slots(
            forecast.hourly, results, min_duration, require_passing
        )

        if not candidates:
            return TimeSlotRecommendation(
                activity=activity.name,
                search_start=forecast.hourly[0].time,
                search_end=forecast.hourly[-1].time + timedelta(hours=1),
                no_suitable_slots=True,
                no_slots_reason="No time slots meet the requirements",
                min_duration_required=min_duration,
            )

        # Score and rank candidates
        scored_slots = self._score_candidates(candidates, preferred_duration)

        # Sort by score descending
        scored_slots.sort(key=lambda s: s.score, reverse=True)

        # Take top N
        top_slots = scored_slots[:max_slots]

        # Mark the best as optimal
        if top_slots:
            top_slots[0].is_optimal = True

        return TimeSlotRecommendation(
            activity=activity.name,
            search_start=forecast.hourly[0].time,
            search_end=forecast.hourly[-1].time + timedelta(hours=1),
            slots=top_slots,
            optimal_slot=top_slots[0] if top_slots else None,
            min_duration_required=min_duration,
        )

    def _find_contiguous_slots(
        self,
        forecasts: list[HourlyForecast],
        results: list[EvaluationResult],
        min_duration: timedelta,
        require_passing: bool,
    ) -> list[SlotCandidate]:
        """Find contiguous time periods that meet requirements."""
        candidates: list[SlotCandidate] = []
        min_hours = int(min_duration.total_seconds() / 3600)

        # Sliding window approach
        i = 0
        while i < len(forecasts):
            # Check if this hour passes (or we don't require passing)
            if not require_passing or results[i].passed:
                # Start a new candidate
                start_idx = i
                end_idx = i

                # Extend as far as possible
                while end_idx < len(forecasts) - 1:
                    next_idx = end_idx + 1
                    if require_passing and not results[next_idx].passed:
                        break
                    end_idx = next_idx

                # Check if long enough
                num_hours = end_idx - start_idx + 1
                if num_hours >= min_hours:
                    candidates.append(
                        SlotCandidate(
                            start_idx=start_idx,
                            end_idx=end_idx,
                            forecasts=forecasts[start_idx : end_idx + 1],
                            results=results[start_idx : end_idx + 1],
                        )
                    )

                # Move past this block
                i = end_idx + 1
            else:
                i += 1

        return candidates

    def _score_candidates(
        self,
        candidates: list[SlotCandidate],
        preferred_duration: timedelta,
    ) -> list[TimeSlot]:
        """Score and convert candidates to TimeSlots."""
        slots: list[TimeSlot] = []
        preferred_hours = preferred_duration.total_seconds() / 3600

        for candidate in candidates:
            # Base score from weather conditions
            base_score = candidate.avg_score

            # Duration bonus/penalty
            duration_hours = candidate.duration.total_seconds() / 3600
            if duration_hours >= preferred_hours:
                # Bonus for meeting preferred duration, but diminishing returns
                duration_factor = min(1.0, preferred_hours / duration_hours) * 1.1
            else:
                # Penalty for shorter than preferred
                duration_factor = duration_hours / preferred_hours

            final_score = base_score * duration_factor

            # Calculate averages for summary
            temps = [f.temperature_c for f in candidate.forecasts]
            clouds = [
                f.cloud_cover.total_percent
                for f in candidate.forecasts
                if f.cloud_cover
            ]
            precips = [
                f.precipitation.probability_percent
                for f in candidate.forecasts
                if f.precipitation
            ]
            winds = [
                f.wind.speed_ms for f in candidate.forecasts if f.wind
            ]

            # Build advantages/disadvantages
            advantages: list[str] = []
            disadvantages: list[str] = []

            avg_temp = sum(temps) / len(temps) if temps else None
            if avg_temp is not None:
                if 15 <= avg_temp <= 25:
                    advantages.append("Comfortable temperature")
                elif avg_temp < 5:
                    disadvantages.append("Cold conditions")
                elif avg_temp > 30:
                    disadvantages.append("Hot conditions")

            avg_cloud = sum(clouds) / len(clouds) if clouds else None
            if avg_cloud is not None:
                if avg_cloud < 20:
                    advantages.append("Clear skies")
                elif avg_cloud > 70:
                    disadvantages.append("Cloudy conditions")

            max_precip = max(precips) if precips else 0
            if max_precip < 10:
                advantages.append("Low precipitation chance")
            elif max_precip > 50:
                disadvantages.append("Significant precipitation risk")

            avg_wind = sum(winds) / len(winds) if winds else None
            if avg_wind is not None:
                if avg_wind < 3:
                    advantages.append("Calm conditions")
                elif avg_wind > 8:
                    disadvantages.append("Windy conditions")

            slots.append(
                TimeSlot(
                    start=candidate.start_time,
                    end=candidate.end_time,
                    score=min(100, max(0, final_score)),
                    avg_temperature_c=avg_temp,
                    avg_cloud_cover_percent=avg_cloud,
                    max_precipitation_percent=max_precip,
                    avg_wind_speed_ms=avg_wind,
                    advantages=advantages,
                    disadvantages=disadvantages,
                )
            )

        return slots


def find_optimal_slots(
    forecast: Forecast,
    activity: Activity,
    min_duration: timedelta = timedelta(minutes=30),
    max_slots: int = 3,
) -> TimeSlotRecommendation:
    """Convenience function to find optimal time slots.

    Args:
        forecast: Weather forecast to search
        activity: Activity with requirements
        min_duration: Minimum slot duration
        max_slots: Maximum slots to return

    Returns:
        TimeSlotRecommendation with best slots
    """
    finder = TimeSlotFinder()
    return finder.find_slots(
        forecast=forecast,
        activity=activity,
        min_duration=min_duration,
        max_slots=max_slots,
    )
