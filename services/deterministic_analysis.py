"""
deterministic_analysis.py

Orchestriert alle deterministischen Analysen.

Diese Schicht enthält keine Businesslogik,
sondern ruft die einzelnen Analyzer auf.
"""

from __future__ import annotations

from models.parsed_workout import ParsedWorkout
from models.deterministic_analysis import DeterministicAnalysis

from analyzers.bewegungsmuster import (
    analyze_bewegungsmuster,
)

from analyzers.categories import (
    analyze_movement_categories,
)

from analyzers.muskelgruppen import (
    analyze_muskelgruppen,
)

from analyzers.movements import (
    analyze_movements,
)

from analyzers.trainingsvolumen import (
    analyze_trainingsvolumen,
)


def derive_deterministic_analysis(
    *,
    parsed_workout: ParsedWorkout,
) -> DeterministicAnalysis:
    """
    Führt alle deterministischen Analysen durch.
    """

    result = DeterministicAnalysis()

    result.bewegungsmuster = analyze_bewegungsmuster(
        parsed_workout
    )

    result.muskelgruppen = analyze_muskelgruppen(
        parsed_workout
    )

    result.movement_categories = analyze_movement_categories(
        parsed_workout
    )

    result.movements = analyze_movements(
        parsed_workout
    )

    result.trainingsvolumen = analyze_trainingsvolumen(
        parsed_workout
    )

    return result