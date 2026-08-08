from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass(slots=True)
class TrainingAnalysis:
    """
    Regelbasierte Analyse der Trainingshistorie.

    Enthält ausschließlich objektiv berechnete
    Erkenntnisse aus bisherigen Workouts.
    """

    readiness: dict = field(default_factory=dict)

    weekly_focus: dict = field(default_factory=dict)

    positive_observations: list[dict] = field(
        default_factory=list
    )

    top_findings: list[dict] = field(
    default_factory=list
)

    missing_movements: list[str] = field(
        default_factory=list
    )

    movement_coverage: dict = field(
        default_factory=dict
    )

    trends: dict = field(default_factory=dict)

    overview: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)