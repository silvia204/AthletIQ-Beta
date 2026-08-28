"""
coach.py

Erstellt das finale Coach-Feedback auf Basis bereits berechneter
History-Analysen.
"""

from __future__ import annotations

from models.training_analysis import TrainingAnalysis

from services.coach_context import (
    build_history_coach_context,
)

from services.mistral_coach import (
    build_coach_with_mistral,
    build_daily_coach_tips,
)


def build_coach_feedback(
    *,
    training_analysis: TrainingAnalysis,
    readiness: dict,
    weekly_focus: dict,
    positive_observations: list[dict],
    history_summary: dict,
    sportart: str,
    level: str,
    injuries: str | None,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """
    Erstellt das History-Coach-Feedback.

    history_summary wird nur lokal zur deterministischen Ableitung
    von Recency/Trainingsrhythmus verwendet. Die vollständige
    history_summary wird nicht an Mistral weitergereicht.
    """

    coach_context = build_history_coach_context(
        training_analysis=training_analysis,
        readiness=readiness,
        weekly_focus=weekly_focus,
        positive_observations=positive_observations,
        history_summary=history_summary,
        sportart=sportart,
    )

    return build_coach_with_mistral(
        coach_context=coach_context,
        sportart=sportart,
        level=level,
        injuries=injuries,
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
    return build_daily_coach_tips(
        readiness=readiness,
        weekly_focus=weekly_focus,
        training_analysis=training_analysis,
        history_summary=history_summary,
        sportart=sportart,
        level=level,
        injuries=injuries,
        api_key=api_key,
        model=model,
    )
