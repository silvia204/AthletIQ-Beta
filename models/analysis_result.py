from __future__ import annotations
from dataclasses import dataclass, field

# ==========================================================
# Analysis Result
# ==========================================================

@dataclass(slots=True)
class AnalysisResult:
    """
    Ergebnis der Trainingsanalyse.

    Dieses Objekt wird ausschließlich aus einem ParsedWorkout
    erzeugt.

    Es enthält KEINE Rohdaten des Workouts.
    """

    # ------------------------------------------------------
    # Bewegungsmuster
    # ------------------------------------------------------

    bewegungsmuster: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # Muskelgruppen
    # ------------------------------------------------------

    muskelgruppen: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # Trainingsziele
    # ------------------------------------------------------

    trainingsziele: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # Belastungsarten
    # ------------------------------------------------------

    belastungsarten: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # Trainingsvolumen
    # ------------------------------------------------------

    trainingsvolumen: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # Workout-Klassifikation
    # ------------------------------------------------------

    klassifikation: dict = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # CrossFit
    # ------------------------------------------------------

    crossfit_movements: dict[str, float] = field(
        default_factory=dict
    )

    # ------------------------------------------------------
    # Hinweise
    # ------------------------------------------------------

    warnings: list[str] = field(
        default_factory=list
    )

    review_required: bool = False