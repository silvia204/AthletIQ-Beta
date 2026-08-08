"""
mistral_coach.py

Erstellt das finale Coach-Feedback mit Mistral.

Diese Schicht enthält ausschließlich
Prompt Building und den LLM-Aufruf.
"""

from __future__ import annotations

import json

from models.parsed_workout import ParsedWorkout
from models.deterministic_analysis import (
    DeterministicAnalysis,
)
from models.workout_interpretation import (
    WorkoutInterpretation,
)
from models.training_analysis import (
    TrainingAnalysis,
)

from prompts.coach import COACH_PROMPT

from services.mistral_service import (
    call_mistral,
)


def build_coach_with_mistral(
    *,
    parsed_workout: ParsedWorkout,
    deterministic_analysis: DeterministicAnalysis,
    workout_interpretation: WorkoutInterpretation,
    training_analysis: TrainingAnalysis,
    readiness: dict,
    weekly_focus: dict,
    positive_observations: list[str],
    history_summary: dict,
    sportart: str,
    level: str,
    workout_rpe: int | None,
    duration_minutes: int | None,
    injuries: str | None,
    comment: str | None,
    api_key: str,
    model: str,
) -> str:
    """
    Erstellt den Prompt und ruft Mistral auf.
    """

    prompt = f"""
{COACH_PROMPT}

SPORTART

{sportart}

LEVEL

{level}

WORKOUT RPE

{workout_rpe}

TRAININGSDAUER

{duration_minutes}

BESCHWERDEN

{injuries or "Keine"}

KOMMENTAR

{comment or "Keiner"}

----------------------------------------

PARSED WORKOUT

{json.dumps(parsed_workout.to_dict(), ensure_ascii=False, indent=2)}

----------------------------------------

DETERMINISTIC ANALYSIS

{json.dumps(deterministic_analysis.to_dict(), ensure_ascii=False, indent=2)}

----------------------------------------

WORKOUT INTERPRETATION

{json.dumps(workout_interpretation.to_dict(), ensure_ascii=False, indent=2)}

----------------------------------------

TRAINING ANALYSIS

{json.dumps(training_analysis.to_dict(), ensure_ascii=False, indent=2)}

----------------------------------------

READINESS

{json.dumps(readiness, ensure_ascii=False, indent=2)}

----------------------------------------

WEEKLY FOCUS

{json.dumps(weekly_focus, ensure_ascii=False, indent=2)}

----------------------------------------

POSITIVE OBSERVATIONS

{json.dumps(positive_observations, ensure_ascii=False, indent=2)}

----------------------------------------

HISTORY SUMMARY

{json.dumps(history_summary, ensure_ascii=False, indent=2)}
""".strip()

    return call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )