"""Deterministische Ableitung der Trainingsziele aus ParsedWorkout."""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout, WorkoutElement
from services.movement_registry import MovementCategory, find_movement


def _movement(element: WorkoutElement):
    for name in (element.movement.raw_name, element.movement.canonical_name):
        if name and (movement := find_movement(name)) is not None:
            return movement
    return None


def _effective_reps(element: WorkoutElement, rounds: int, rep_scheme: list[int] | None) -> int:
    sets = element.sets or 1
    if rep_scheme and element.reps is None:
        return sum(rep_scheme) * rounds * sets
    return (element.reps or 0) * sets * rounds


def analyze_trainingsziele(parsed_workout: ParsedWorkout) -> dict[str, float]:
    """Erzeugt reproduzierbare Trainingsziel-Scores ohne LLM-Abhängigkeit."""
    goals: Counter[str] = Counter()

    for segment in parsed_workout.segments:
        rounds = segment.rounds or 1
        text = " ".join(
            str(value or "").casefold()
            for value in (segment.type, segment.name, segment.notes)
        )

        if any(term in text for term in ("skill", "technik", "technique")):
            goals["technique"] += 1.0
        if any(term in text for term in ("mobility", "mobilität", "mobilitaet")):
            goals["mobility"] += 1.0
        if any(term in text for term in ("recovery", "regeneration", "cool down", "cooldown")):
            goals["recovery"] += 1.0

        conditioning = any(
            term in text
            for term in ("conditioning", "metcon", "amrap", "emom", "for time", "rft", "chipper", "interval")
        ) or (segment.rounds or 0) >= 3 or segment.time_cap_minutes is not None

        for element in segment.elements:
            movement = _movement(element)
            if movement is None:
                continue

            reps = _effective_reps(element, rounds, segment.rep_scheme)
            per_set_reps = element.reps or (max(segment.rep_scheme) if segment.rep_scheme else 0)
            intensity = element.intensity
            high_strength = (
                (intensity.percent_1rm is not None and intensity.percent_1rm >= 80)
                or (intensity.prescribed_rpe is not None and intensity.prescribed_rpe >= 8)
                or (intensity.rir is not None and intensity.rir <= 2)
            )

            name = movement.display_name.casefold()
            explosive = any(term in name for term in ("snatch", "clean", "jerk", "box jump"))

            if movement.category == MovementCategory.MONOSTRUCTURAL:
                goals["aerobic_base"] += 1.0
                threshold_signal = any(
                    term in text
                    for term in ("threshold", "schwelle", "tempo", "interval")
                ) or (
                    segment.time_cap_minutes is not None
                    and segment.time_cap_minutes <= 20
                )
                if threshold_signal:
                    goals["threshold"] += 0.5
                continue

            if explosive:
                goals["explosive_strength"] += 1.0

            if high_strength and (per_set_reps == 0 or per_set_reps <= 6):
                goals["max_strength"] += 1.0
            elif element.sets and 6 <= per_set_reps <= 15 and not conditioning:
                goals["hypertrophy"] += 1.0
            elif conditioning or reps >= 15:
                goals["strength_endurance"] += 1.0
            else:
                goals["strength_endurance"] += 0.5

        if conditioning and len(segment.elements) >= 2:
            goals["anaerobic_capacity"] += 0.5

    return {key: round(value, 2) for key, value in goals.items() if value > 0}
