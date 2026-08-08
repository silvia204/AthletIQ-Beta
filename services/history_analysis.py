"""
history_analysis.py

Orchestriert die regelbasierte Analyse der Trainingshistorie.
"""

from __future__ import annotations

from models.deterministic_analysis import (
    DeterministicAnalysis,
)
from models.training_analysis import (
    TrainingAnalysis,
)
from models.workout_interpretation import (
    WorkoutInterpretation,
)

from analyzers.history.readiness import (
    analyze_readiness,
)

from analyzers.history.weekly_focus import (
    analyze_weekly_focus,
)

from analyzers.history.positive_observations import (
    analyze_positive_observations,
)

from analyzers.history.movement_coverage import (
    analyze_movement_coverage,
)

from analyzers.history.top_findings import (
    analyze_top_findings,
)

from analyzers.history.trends import (
    analyze_trends,
)

from analyzers.history.overview import (
    analyze_overview,
)


def analyze_history(
    *,
    history_summary: dict,
    deterministic_analysis: DeterministicAnalysis,
    workout_interpretation: WorkoutInterpretation,
) -> TrainingAnalysis:
    """
    Analysiert die Trainingshistorie und kombiniert
    sie mit dem aktuellen Workout.
    """

    readiness = analyze_readiness(
        history_summary,
    )

    weekly_focus = analyze_weekly_focus(
        history_summary=history_summary,
        readiness=readiness,
    )

    movement_coverage = analyze_movement_coverage(
        history_summary,
    )

    positive_observations = (
        analyze_positive_observations(
            history_summary=history_summary,
            readiness=readiness,
            movement_coverage=movement_coverage,
        )
    )

    trends = analyze_trends(
        history_summary,
    )

    overview = analyze_overview(
        history_summary,
    )

    top_findings = analyze_top_findings(
        readiness=readiness,
        weekly_focus=weekly_focus,
        trends=trends,
        overview=overview,
        movement_coverage=movement_coverage,
        workout_interpretation=workout_interpretation,
    )

    return TrainingAnalysis(

        readiness=readiness,

        weekly_focus=weekly_focus,

        positive_observations=positive_observations,

        top_findings=top_findings,

        movement_coverage=movement_coverage,

        missing_movements=movement_coverage.get(
            "missing",
            [],
        ),

        trends=trends,

        overview=overview,
    )