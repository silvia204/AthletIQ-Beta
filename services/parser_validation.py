"""
parser_validation.py

Validiert ein ParsedWorkout.
"""

from __future__ import annotations

from models.parsed_workout import ParsedWorkout


def validate_parsed_workout(
    parsed_workout: ParsedWorkout,
) -> None:
    """
    Prüft die grundlegende Konsistenz eines ParsedWorkouts.

    Wirft ValueError bei ungültigen Daten.
    """

    if parsed_workout is None:
        raise ValueError(
            "ParsedWorkout darf nicht None sein."
        )

    if not parsed_workout.segments:
        raise ValueError(
            "ParsedWorkout enthält keine Segmente."
        )

    for segment in parsed_workout.segments:

        if not segment.elements:
            continue

        for element in segment.elements:

            if not element.movement.raw_name.strip():
                raise ValueError(
                    "Movement ohne Namen gefunden."
                )