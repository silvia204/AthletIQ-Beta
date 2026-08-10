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

    for segment_index, segment in enumerate(
        parsed_workout.segments
    ):

        if not segment.elements:
            continue

        for element_index, element in enumerate(
            segment.elements
        ):

            raw_name = (
                element.movement.raw_name or ""
            ).strip()

            canonical_name = (
                element.movement.canonical_name or ""
            ).strip()

            if not raw_name:
                raise ValueError(
                    "Movement ohne raw_name gefunden. "
                    f"Segment {segment_index + 1}, "
                    f"Element {element_index + 1}: "
                    f"raw_name={element.movement.raw_name!r}, "
                    f"canonical_name="
                    f"{element.movement.canonical_name!r}"
                )