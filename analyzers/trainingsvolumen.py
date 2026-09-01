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

        rep_scheme = (
            segment.rep_scheme
            if segment.rep_scheme
            else None
        )

        rep_scheme_total = (
            sum(rep_scheme)
            if rep_scheme
            else None
        )

        for element in segment.elements:

            sets = element.sets or 1

            # ------------------------------------------------
            # EFFEKTIVE WIEDERHOLUNGEN
            # ------------------------------------------------

            if (
                rep_scheme_total is not None
                and element.reps is None
            ):
                # Beispiel:
                # 21-15-9 Burpees + Pull-ups
                #
                # Pro Movement:
                # 21 + 15 + 9 = 45 Reps
                effective_reps = (rep_scheme_total * rounds)

            else:
                reps = element.reps or 0

                effective_reps = (
                    reps
                    * sets
                    * rounds
                )

            # Wiederholungen
            volume.repetitions += (
                effective_reps
            )

            # Distanz
            if element.distance is not None:

                if element.distance_unit == "m":
                    volume.distance_m += (
                        element.distance
                        * rounds
                        * sets
                    )

                elif element.distance_unit == "km":
                    volume.distance_m += (
                        element.distance
                        * 1000
                        * rounds
                        * sets
                    )

            # Dauer
            if element.duration is not None:

                if element.duration_unit in (
                    "s",
                    "sec",
                    "seconds",
                ):
                    volume.duration_seconds += (
                        element.duration
                        * rounds
                        * sets
                    )

                elif element.duration_unit in (
                    "min",
                    "minute",
                    "minutes",
                ):
                    volume.duration_seconds += (
                        element.duration
                        * 60
                        * rounds
                        * sets
                    )

            # Calories
            if element.calories is not None:
                volume.calories += (
                    element.calories
                    * rounds
                    * sets
                )

            # Externe Last (Tonnage)
            if (
                element.intensity.weight is not None
                and element.intensity.weight_unit == "kg"
            ):
                volume.external_load_kg += (
                    element.intensity.weight
                    * effective_reps
                )

    return volume