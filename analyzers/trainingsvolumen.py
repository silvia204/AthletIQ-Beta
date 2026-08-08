"""
trainingsvolumen.py

Ermittelt das objektive Trainingsvolumen
eines ParsedWorkouts.
"""

from __future__ import annotations

from models.parsed_workout import ParsedWorkout
from models.training_volume import TrainingVolume


def analyze_trainingsvolumen(
    parsed_workout: ParsedWorkout,
) -> TrainingVolume:
    """
    Ermittelt alle objektiv messbaren
    Trainingsumfangskennzahlen.
    """

    volume = TrainingVolume()

    for segment in parsed_workout.segments:

        rounds = segment.rounds or 1

        for element in segment.elements:

            sets = element.sets or 1
            reps = element.reps or 0

            multiplier = rounds * sets

            # Wiederholungen
            volume.repetitions += reps * multiplier

            # Distanz
            if element.distance is not None:

                if element.distance_unit == "m":
                    volume.distance_m += (
                        element.distance * rounds
                    )

                elif element.distance_unit == "km":
                    volume.distance_m += (
                        element.distance * 1000 * rounds
                    )

            # Dauer
            if element.duration is not None:

                if element.duration_unit in (
                    "s",
                    "sec",
                    "seconds",
                ):
                    volume.duration_seconds += (
                        element.duration * rounds
                    )

                elif element.duration_unit in (
                    "min",
                    "minute",
                    "minutes",
                ):
                    volume.duration_seconds += (
                        element.duration * 60 * rounds
                    )

            # Calories
            if element.calories is not None:
                volume.calories += (
                    element.calories * rounds
                )

            # Externe Last (Tonnage)
            if (
                element.intensity.weight is not None
                and element.intensity.weight_unit == "kg"
            ):
                volume.external_load_kg += (
                    element.intensity.weight
                    * reps
                    * multiplier
                )

    return volume