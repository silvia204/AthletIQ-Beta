"""
muskelgruppen.py

Ermittelt die beanspruchten Muskelgruppen
eines Workouts.
"""

from __future__ import annotations

from collections import Counter

from models.parsed_workout import ParsedWorkout

from analyzers.utils import iter_movements


def analyze_muskelgruppen(
    parsed_workout: ParsedWorkout,
) -> dict[str, int]:
    """
    Ermittelt die Häufigkeit aller primären Muskelgruppen
    eines Workouts.
    """

    muscles: Counter[str] = Counter()

    for movement in iter_movements(parsed_workout):

        for muscle in movement.muscle_groups:
            muscles[muscle.name.lower()] += 1

    return dict(muscles)