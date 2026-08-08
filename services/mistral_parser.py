"""
mistral_parser.py

Enthält ausschließlich die Kommunikation mit Mistral
zur Erstellung eines ParsedWorkout.
"""

from __future__ import annotations

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


def _build_parsed_workout(
    data: dict,
) -> ParsedWorkout:

    workout = ParsedWorkout()

    for segment_data in data.get(
        "segments",
        [],
    ):

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