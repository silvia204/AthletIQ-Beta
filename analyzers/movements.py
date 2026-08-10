"""
movements.py

Ermittelt alle bekannten CrossFit Movements eines Workouts.
"""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout

from analyzers.utils import iter_movements


def analyze_movements(
    parsed_workout: ParsedWorkout,
) -> dict[str, int]:
    """
    Ermittelt alle bekannten CrossFit Movements
    eines Workouts.

    Es werden ausschließlich Movements berücksichtigt,
    die in der zentralen Movement Registry mit
    is_crossfit_movement=True gekennzeichnet sind.
    """

    movements = Counter()

    for movement in iter_movements(
        parsed_workout
    ):

        if not movement.is_crossfit_movement:
            continue

        movements[
            movement.movement_id
        ] += 1

    return dict(movements)