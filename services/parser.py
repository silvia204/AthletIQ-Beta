"""
parser.py

Öffentliche Schnittstelle zum Workout-Parser.
Der Rest der Anwendung kennt ausschließlich parse_workout().
Diese Datei enthält bewusst keinerlei Mistral-spezifische Logik.
"""

from __future__ import annotations

from models.parsed_workout import ParsedWorkout

from services.mistral_parser import parse_with_mistral
from services.parser_validation import validate_parsed_workout


def parse_workout(
    *,
    workout_text: str,
    api_key: str,
    model: str,
) -> ParsedWorkout:
    """
    Erstellt aus einem Workout-Text ein ParsedWorkout.

    Ablauf

    Workout-Text
            │
            ▼
    Mistral Parser
            │
            ▼
    ParsedWorkout
            │
            ▼
    Validierung
            │
            ▼
    Rückgabe
    """

    parsed_workout = parse_with_mistral(
        workout_text=workout_text,
        api_key=api_key,
        model=model,
    )

    validate_parsed_workout(parsed_workout)

    return parsed_workout