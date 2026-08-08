"""
categories.py

Ermittelt die Häufigkeit der Movement Categories
eines Workouts.
"""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout

from analyzers.utils import iter_movements


def analyze_movement_categories(
    parsed_workout: ParsedWorkout,
) -> dict[str, int]:
    """
    Ermittelt die Häufigkeit aller Movement Categories
    eines Workouts.
    """

    categories: Counter[str] = Counter()

    for movement in iter_movements(parsed_workout):
        categories[movement.category.name.lower()] += 1

    return dict(categories)