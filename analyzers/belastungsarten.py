"""Deterministische Ableitung der Belastungsarten aus ParsedWorkout."""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout, WorkoutElement
from services.movement_registry import MovementCategory, find_movement


def _movement(element: WorkoutElement):
    for name in (element.movement.raw_name, element.movement.canonical_name):
        if name and (movement := find_movement(name)) is not None:
            return movement
    return None


def analyze_belastungsarten(parsed_workout: ParsedWorkout) -> dict[str, float]:
    """Erzeugt reproduzierbare Belastungsart-Scores ohne LLM-Abhängigkeit."""
    loads: Counter[str] = Counter()

    for segment in parsed_workout.segments:
        text = " ".join(
            str(value or "").casefold()
            for value in (segment.type, segment.name, segment.notes)
        )
        conditioning = any(
            term in text
            for term in ("conditioning", "metcon", "amrap", "emom", "for time", "rft", "chipper", "interval")
        ) or (segment.rounds or 0) >= 3 or segment.time_cap_minutes is not None

        categories: set[MovementCategory] = set()

        for element in segment.elements:
            movement = _movement(element)
            if movement is None:
                continue

            categories.add(movement.category)
            intensity = element.intensity
            name = movement.display_name.casefold()

            if movement.category == MovementCategory.MONOSTRUCTURAL:
                loads["cardio"] += 1.0
                loads["cyclic"] += 1.0
            else:
                loads["strength"] += 1.0

            if intensity.weight is not None or intensity.percent_1rm is not None:
                loads["mechanical"] += 1.0

            if (
                (intensity.percent_1rm is not None and intensity.percent_1rm >= 80)
                or (intensity.prescribed_rpe is not None and intensity.prescribed_rpe >= 8)
                or (intensity.rir is not None and intensity.rir <= 2)
            ):
                loads["high_intensity"] += 1.0
                loads["neuromuscular"] += 0.5
            elif (
                (intensity.percent_1rm is not None and intensity.percent_1rm >= 60)
                or (intensity.prescribed_rpe is not None and intensity.prescribed_rpe >= 6)
            ):
                loads["moderate_intensity"] += 1.0
            elif any(v is not None for v in (intensity.percent_1rm, intensity.prescribed_rpe, intensity.rir)):
                loads["low_intensity"] += 1.0

            if any(term in name for term in ("run", "jump", "burpee")):
                loads["impact"] += 1.0
            if any(term in name for term in ("hold", "plank", "sit")) and "sit up" not in name:
                loads["isometric"] += 1.0
            if intensity.tempo and str(intensity.tempo)[0:1].isdigit() and str(intensity.tempo)[0] != "0":
                loads["eccentric"] += 1.0

        if conditioning:
            loads["metabolic"] += max(1.0, float(len(segment.elements)))

        if MovementCategory.MONOSTRUCTURAL in categories and len(categories) > 1:
            loads["mixed"] += 1.0

    return {key: round(value, 2) for key, value in loads.items() if value > 0}
