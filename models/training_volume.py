from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TrainingVolume:
    """
    Objektive Trainingsumfangskennzahlen eines Workouts.

    Enthält ausschließlich messbare Größen aus dem ParsedWorkout.
    Keine Interpretation.
    """

    # Gesamtzahl aller Wiederholungen
    repetitions: int = 0

    # Gesamtdistanz in Metern
    distance_m: float = 0.0

    # Gesamte Calories
    calories: int = 0

    # Gesamtdauer in Sekunden
    duration_seconds: float = 0.0

    # Gesamttonnage (Gewicht × Wiederholungen)
    external_load_kg: float = 0.0