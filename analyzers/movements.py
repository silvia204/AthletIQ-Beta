"""
movements.py

Ermittelt alle bekannten Bewegungen eines Workouts.
"""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout

from analyzers.utils import iter_movements


def analyze_movements(
    parsed_workout: ParsedWorkout,
) -> dict[str, int]:
    """
    Ermittelt alle bekannten Bewegungen
    eines Workouts.
    """

    movements = Counter()

    for movement in iter_movements(parsed_workout):
        movements[movement.movement_id] += 1

    return dict(movements)