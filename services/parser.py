"""
parser.py

Öffentliche Schnittstelle zum Workout-Parser.
Der Rest der Anwendung kennt ausschließlich parse_workout().
Diese Datei enthält bewusst keinerlei Mistral-spezifische Logik.
"""

from __future__ import annotations

from models.parsed_workout import ParsedWorkout

from services.mistral_parser import (
    parse_image_with_mistral,
    parse_with_mistral,
)
from services.parser_validation import validate_parsed_workout


def parse_workout(
    *,
    api_key: str,
    model: str,
    workout_text: str | None = None,
    image_data: bytes | None = None,
    image_mime_type: str | None = None,
) -> ParsedWorkout:
    """
    Erstellt aus Workout-Text oder einem Workout-Foto ein ParsedWorkout.
    """

    has_text = bool(workout_text and workout_text.strip())
    has_image = image_data is not None and len(image_data) > 0

    if has_text and has_image:
        raise ValueError(
            "Bitte übergib entweder Workout-Text oder ein Bild, nicht beides."
        )

    if has_image:
        parsed_workout = parse_image_with_mistral(
            image_data=image_data,
            image_mime_type=image_mime_type or "image/jpeg",
            api_key=api_key,
            model=model,
        )
    elif has_text:
        parsed_workout = parse_with_mistral(
            workout_text=workout_text.strip(),
            api_key=api_key,
            model=model,
        )
    else:
        raise ValueError(
            "Es wurde weder Workout-Text noch ein Workout-Foto übergeben."
        )

    validate_parsed_workout(parsed_workout)
    return parsed_workout