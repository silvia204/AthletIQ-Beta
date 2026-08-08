"""
bewegungsmuster.py
"""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout

from analyzers.utils import iter_movements


def analyze_bewegungsmuster(
    parsed_workout: ParsedWorkout,
) -> dict[str, int]:

    patterns = Counter()

    for movement in iter_movements(parsed_workout):

        for pattern in movement.movement_patterns:

            patterns[pattern] += 1

    return dict(patterns)