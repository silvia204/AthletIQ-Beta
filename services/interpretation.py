"""
interpretation.py

Erzeugt die sportwissenschaftliche Interpretation
eines Workouts.

Diese Schicht verbindet die App mit dem LLM.
"""

from __future__ import annotations

from models.parsed_workout import ParsedWorkout
from models.deterministic_analysis import (
    DeterministicAnalysis,
)
from models.workout_interpretation import (
    WorkoutInterpretation,
)

from services.mistral_interpreter import (
    interpret_with_mistral,
)


def interpret_workout(
    *,
    parsed_workout: ParsedWorkout,
    deterministic_analysis: DeterministicAnalysis,
    sportart: str,
    api_key: str,
    model: str,
) -> WorkoutInterpretation:
    """
    Führt die sportwissenschaftliche
    Interpretation durch.
    """

    return interpret_with_mistral(
        parsed_workout=parsed_workout,
        deterministic_analysis=deterministic_analysis,
        sportart=sportart,
        api_key=api_key,
        model=model,
    )