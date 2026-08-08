"""
mistral_interpreter.py

Kommuniziert mit Mistral, um ein Workout sportwissenschaftlich zu interpretieren.
"""
from __future__ import annotations
from dataclasses import asdict

import json

from models.parsed_workout import ParsedWorkout
from models.deterministic_analysis import (
    DeterministicAnalysis,
)
from models.workout_interpretation import (
    WorkoutInterpretation,
)

from prompts.workout_interpretation import (
    WORKOUT_INTERPRETATION_PROMPT,
)

from services.mistral_service import (
    call_mistral,
    remove_markdown_code_fence,
)


def interpret_with_mistral(
    *,
    parsed_workout: ParsedWorkout,
    deterministic_analysis: DeterministicAnalysis,
    sportart: str,
    api_key: str,
    model: str,
) -> WorkoutInterpretation:
    """
    Führt die sportwissenschaftliche
    Interpretation eines Workouts durch.
    """

    prompt = (
        f"{WORKOUT_INTERPRETATION_PROMPT}\n\n"
        f"Sportart:\n{sportart}\n\n"
        f"ParsedWorkout:\n"
        f"{json.dumps(asdict(parsed_workout), indent=2)}\n\n"
        f"DeterministicAnalysis:\n"
        f"{json.dumps(deterministic_analysis.to_dict(), indent=2)}"
    )
    
    print("===== INTERPRETER PROMPT =====")
    print(prompt)
    print("==============================")

    response = call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )

    print("===== INTERPRETER RESPONSE =====")
    print(repr(response))
    print("================================")

    response = remove_markdown_code_fence(response)
    response_json = json.loads(response)

    print("===== INTERPRETER JSON =====")
    print(response_json)
    print("============================")

    return _build_workout_interpretation(
        response_json
    )


def _build_workout_interpretation(
    data: dict,
) -> WorkoutInterpretation:

    return WorkoutInterpretation(

        trainingsziele=data.get(
            "trainingsziele",
            {},
        ),

        belastungsarten=data.get(
            "belastungsarten",
            {},
        ),

        klassifikation=data.get(
            "klassifikation",
            {},
        ),

        trainingsintention=data.get(
            "trainingsintention",
            "",
        ),

        besonderheiten=data.get(
            "besonderheiten",
            [],
        ),

        confidence=data.get(
            "confidence",
        ),
    )