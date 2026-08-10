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

    Für die Registry-Suche wird zuerst der vom Parser
    erkannte Rohname verwendet. Falls dieser nicht in der
    Movement Registry gefunden wird, wird canonical_name
    als Fallback versucht.

    Unbekannte Bewegungen werden übersprungen.
    """

    for segment in parsed_workout.segments:

        for element in segment.elements:

            raw_name = (
                element.movement.raw_name or ""
            ).strip()

            canonical_name = (
                element.movement.canonical_name or ""
            ).strip()

            movement = None

            # Zuerst den tatsächlichen Namen aus dem
            # Workout gegen Varianten und Aliase prüfen.
            if raw_name:
                movement = find_movement(
                    raw_name
                )

            # Falls der Rohname nicht gefunden wurde,
            # den vom Parser erzeugten canonical_name
            # als Fallback verwenden.
            if (
                movement is None
                and canonical_name
            ):
                movement = find_movement(
                    canonical_name
                )

            # Unbekannte Bewegungen werden von den
            # deterministischen Analyzern ignoriert.
            if movement is None:
                continue

            yield movement