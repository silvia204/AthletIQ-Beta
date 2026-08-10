"""
coach.py

Erstellt das finale Coach-Feedback.

Der Coach analysiert keine Workouts.
Er formuliert ausschließlich Coaching auf Basis
bereits berechneter Daten.
"""

from __future__ import annotations

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

from services.mistral_coach import (
    build_coach_with_mistral,
    build_daily_coach_tips,
)


def build_coach_feedback(
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
    Erstellt das finale Coach-Feedback.
    """

    return build_coach_with_mistral(
        parsed_workout=parsed_workout,
        deterministic_analysis=deterministic_analysis,
        workout_interpretation=workout_interpretation,
        training_analysis=training_analysis,
        readiness=readiness,
        weekly_focus=weekly_focus,
        positive_observations=positive_observations,
        history_summary=history_summary,
        sportart=sportart,
        level=level,
        workout_rpe=workout_rpe,
        duration_minutes=duration_minutes,
        injuries=injuries,
        comment=comment,
        api_key=api_key,
        model=model,
    )


def build_daily_tips(
    *,
    readiness: dict,
    weekly_focus: dict,
    training_analysis: TrainingAnalysis,
    history_summary: dict,
    sportart: str,
    level: str,
    workout_rpe: int | None,
    duration_minutes: int | None,
    injuries: str | None,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """
    Erstellt die drei kompakten Daily-Coach-Tipps
    für Training, Ernährung und Recovery.
    """

    return build_daily_coach_tips(
        readiness=readiness,
        weekly_focus=weekly_focus,
        training_analysis=training_analysis,
        history_summary=history_summary,
        sportart=sportart,
        level=level,
        workout_rpe=workout_rpe,
        duration_minutes=duration_minutes,
        injuries=injuries,
        api_key=api_key,
        model=model,
    )