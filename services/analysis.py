"""
analysis.py

Orchestriert die komplette Workout-Analyse.

Pipeline:

ParsedWorkout
        │
        ▼
Deterministic Analysis
        │
        ▼
Workout Interpretation
"""

from __future__ import annotations

# Konsolen-Debugausgaben sind standardmäßig deaktiviert.
# Bei Bedarf für lokale Fehlersuche temporär auf True setzen.
DEBUG_CONSOLE_OUTPUT = False

def _debug__debug_print(*args, **kwargs) -> None:
    if DEBUG_CONSOLE_OUTPUT:
        print(*args, **kwargs)

from models.parsed_workout import ParsedWorkout
from models.deterministic_analysis import DeterministicAnalysis
from models.workout_interpretation import WorkoutInterpretation

from services.deterministic_analysis import (
    derive_deterministic_analysis,
)

from services.interpretation import (
    interpret_workout,
)


def analyze_workout(
    *,
    parsed_workout: ParsedWorkout,
    sportart: str,
    api_key: str,
    model: str,
) -> tuple[
    DeterministicAnalysis,
    WorkoutInterpretation,
]:
    """
    Führt die komplette Workout-Analyse durch.

    Ablauf:

    1. Deterministische Analyse
    2. KI-Interpretation
    """

   # _debug_print("1 - starte deterministische Analyse")

    #deterministic_analysis = derive_deterministic_analysis(
    #    parsed_workout=parsed_workout,
    #)

    #-_debug_print("2 - deterministische Analyse fertig")

    #-_debug_print("3 - starte Interpretation")

    workout_interpretation = interpret_workout(
        parsed_workout=parsed_workout,
        deterministic_analysis=deterministic_analysis,
        sportart=sportart,
        api_key=api_key,
        model=model,
    )

    #_debug_print("4 - Interpretation fertig")

    return (
        deterministic_analysis,
        workout_interpretation,
    )