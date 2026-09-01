"""
mistral_parser.py

Enthält ausschließlich die Kommunikation mit Mistral
zur Erstellung eines ParsedWorkout.
"""

from __future__ import annotations

import base64
import json

from models.parsed_workout import (
    ParsedWorkout,
    WorkoutSegment,
    WorkoutElement,
    Movement,
    IntensityPrescription,
)

from prompts.workout_parser import (
    WORKOUT_PARSER_PROMPT,
)

from services.mistral_service import (
    call_mistral,
    remove_markdown_code_fence,
)

def parse_with_mistral(
    *,
    workout_text: str,
    api_key: str,
    model: str,
) -> ParsedWorkout:

    prompt = (
        f"{WORKOUT_PARSER_PROMPT}\n\n"
        f"Workout:\n"
        f"{workout_text}"
    )

    response = call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )

    response = remove_markdown_code_fence(response)
    response_json = json.loads(response)

    return _build_parsed_workout(
        response_json
    )




def parse_image_with_mistral(
    *,
    image_data: bytes,
    image_mime_type: str,
    api_key: str,
    model: str,
) -> ParsedWorkout:
    """Erstellt aus einem Workout-Foto ein ParsedWorkout."""

    if not image_data:
        raise ValueError("Die Bilddaten sind leer.")

    mime_type = str(image_mime_type or "image/jpeg").strip()
    encoded_image = base64.b64encode(image_data).decode("utf-8")

    content = [
        {
            "type": "text",
            "text": (
                f"{WORKOUT_PARSER_PROMPT}\n\n"
                "Lies das Workout aus dem bereitgestellten Bild. "
                "Übernimm nur Informationen, die im Bild erkennbar sind. "
                "Erfinde keine Übungen, Wiederholungen, Gewichte, "
                "Distanzen oder Zeiten."
            ),
        },
        {
            "type": "image_url",
            "image_url": f"data:{mime_type};base64,{encoded_image}",
        },
    ]

    response = call_mistral(
        api_key=api_key,
        model=model,
        content=content,
    )
    response = remove_markdown_code_fence(response)

    try:
        response_json = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Das Vision-Modell hat kein gültiges Workout-JSON geliefert."
        ) from exc

    return _build_parsed_workout(response_json)


def _build_parsed_workout(
    data: dict,
) -> ParsedWorkout:

    workout = ParsedWorkout()

    for segment_data in data.get(
        "segments",
        [],
    ):

        raw_rep_scheme = segment_data.get(
            "rep_scheme"
        )

        rep_scheme: list[int] | None = None

        if isinstance(raw_rep_scheme, list):
            cleaned_rep_scheme = []

            for value in raw_rep_scheme:
                try:
                    parsed_value = int(value)
                except (TypeError, ValueError):
                    continue

                if parsed_value > 0:
                    cleaned_rep_scheme.append(
                        parsed_value
                    )

            if cleaned_rep_scheme:
                rep_scheme = cleaned_rep_scheme

        segment = WorkoutSegment(

            type=segment_data.get(
                "type",
                "unknown",
            ),

            name=segment_data.get(
                "name",
            ),

            rounds=segment_data.get(
                "rounds",
            ),

            rep_scheme=rep_scheme,

            time_cap_minutes=segment_data.get(
                "time_cap_minutes",
            ),

            notes=segment_data.get(
                "notes",
            ),
        )

        for element_data in segment_data.get(
            "elements",
            [],
        ):

            movement = Movement(

                raw_name=element_data.get(
                    "movement",
                    "",
                ),

                canonical_name=element_data.get(
                    "movement",
                    "",
                ),

                equipment=element_data.get(
                    "equipment",
                ),
            )

            intensity = IntensityPrescription(

                weight=element_data.get(
                    "weight",
                ),

                weight_unit=element_data.get(
                    "weight_unit",
                ),

                percent_1rm=element_data.get(
                    "percent_1rm",
                ),

                prescribed_rpe=element_data.get(
                    "prescribed_rpe",
                ),

                rir=element_data.get(
                    "rir",
                ),

                tempo=element_data.get(
                    "tempo",
                ),
            )

            element = WorkoutElement(

                movement=movement,

                reps=element_data.get(
                    "reps",
                ),

                sets=element_data.get(
                    "sets",
                ),

                intensity=intensity,

                distance=element_data.get(
                    "distance",
                ),

                distance_unit=element_data.get(
                    "distance_unit",
                ),

                speed=element_data.get(
                    "speed",
                ),

                speed_unit=element_data.get(
                    "speed_unit",
                ),

                pace=element_data.get(
                    "pace",
                ),

                pace_unit=element_data.get(
                    "pace_unit",
                ),

                duration=element_data.get(
                    "duration",
                ),

                duration_unit=element_data.get(
                    "duration_unit",
                ),

                calories=element_data.get(
                    "calories",
                ),

                notes=element_data.get(
                    "notes",
                ),
            )

            segment.elements.append(
                element
            )

        workout.segments.append(
            segment
        )

    workout.notes = data.get(
        "notes"
    )

    return workout