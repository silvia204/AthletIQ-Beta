"""
utils.py

Gemeinsame Hilfsfunktionen für alle Analyzer.
"""

from __future__ import annotations

from collections.abc import Iterator

from models.parsed_workout import ParsedWorkout
from services.movement_registry import (
    Movement,
    find_movement,
)


def iter_movements(
    parsed_workout: ParsedWorkout,
) -> Iterator[Movement]:
    """
    Iteriert über alle bekannten Bewegungen
    eines ParsedWorkout.

    Unbekannte Bewegungen werden übersprungen.
    """

    for segment in parsed_workout.segments:

        for element in segment.elements:

            movement = find_movement(
                element.movement.canonical_name
            )

            if movement is None:
                continue

            yield movement