from __future__ import annotations
from dataclasses import dataclass, field, asdict


@dataclass(slots=True)
class WorkoutInterpretation:
    """
    Sportwissenschaftliche Interpretation
    eines Workouts.

    Diese Informationen stammen ausschließlich
    aus dem LLM.
    """

    trainingsziele: dict[str, float] = field(
        default_factory=dict
    )

    belastungsarten: dict[str, float] = field(
        default_factory=dict
    )

    klassifikation: dict[str, float] = field(
        default_factory=dict
    )

    trainingsintention: str = ""

    besonderheiten: list[str] = field(
        default_factory=list
    )

    confidence: float | None = None

    def to_dict(self) -> dict:
        """
        Serialisiert die Workout-Interpretation.
        """

        return asdict(self)