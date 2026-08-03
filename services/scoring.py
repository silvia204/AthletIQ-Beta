from typing import Any


def calculate_structural_score(
    exercises: list[dict[str, Any]],
) -> int:
    """
    Erstellt eine grobe strukturelle Belastungsbewertung
    aus den erkannten Workout-Inhalten.
    """

    score = 0

    for exercise in exercises:
        name = str(
            exercise.get("name", "")
        ).casefold()

        details = str(
            exercise.get("details", "")
        ).casefold()

        text = f"{name} {details}"

        if any(
            term in text
            for term in [
                "deadlift",
                "kreuzheben",
                "rdl",
            ]
        ):
            if any(
                term in details
                for term in [
                    "satz",
                    "sätze",
                    "sets",
                ]
            ):
                score += 15
            else:
                score += 10

        if any(
            term in text
            for term in [
                "squat",
                "kniebeuge",
                "thruster",
                "wall ball",
                "lunge",
                "ausfallschritt",
            ]
        ):
            score += 8

        if any(
            term in text
            for term in [
                "clean",
                "snatch",
                "jerk",
                "press",
                "reißen",
                "umsetzen",
                "stoßen",
            ]
        ):
            score += 10

        if any(
            term in text
            for term in [
                "row",
                "rudern",
                "rowing",
            ]
        ):
            score += 6

        if any(
            term in text
            for term in [
                "run",
                "laufen",
                "running",
                "jog",
                "kilometer",
            ]
        ):
            score += 6

        if "burpee" in text:
            score += 5

        if any(
            term in text
            for term in [
                "rft",
                "amrap",
                "emom",
                "for time",
                "chipper",
            ]
        ):
            score += 12

        if any(
            term in text
            for term in [
                "bike",
                "echo bike",
                "assault bike",
            ]
        ):
            score += 6

        if any(
            term in text
            for term in [
                "ski erg",
                "skierg",
                "ski-erg",
            ]
        ):
            score += 6

        if any(
            term in text
            for term in [
                "sled push",
                "sled pull",
                "schlitten",
            ]
        ):
            score += 10

        if any(
            term in text
            for term in [
                "pull-up",
                "pullup",
                "klimmzug",
                "toes to bar",
                "muscle-up",
            ]
        ):
            score += 8

    return score


def get_level_factor(level: str) -> float:
    if "Anfänger" in level:
        return 1.15

    if "Experte" in level:
        return 0.90

    return 1.00


def calculate_load_score(
    *,
    structural_score: int,
    rpe: int,
    duration_minutes: int,
    level: str,
) -> int:
    """
    Kombiniert Session-RPE und strukturellen Workout-Wert.
    """

    level_factor = get_level_factor(level)

    session_rpe_load = duration_minutes * rpe
    structural_load = structural_score * 4

    return int(
        (
            session_rpe_load
            + structural_load
        )
        * level_factor
    )


def get_load_status(
    score: int,
) -> tuple[str, str]:
    """
    Liefert Statustext und Streamlit-Anzeigetyp.
    """

    if score <= 450:
        return (
            "NIEDRIGE BIS MODERATE EINHEITSBELASTUNG",
            "success",
        )

    if score <= 750:
        return (
            "MITTLERE BIS HOHE EINHEITSBELASTUNG",
            "warning",
        )

    return (
        "HOHE GESCHÄTZTE EINHEITSBELASTUNG",
        "error",
    )


from typing import Any

from services.utils import safely_convert_to_float


def calculate_classification_dimensions(
    classified_workout: dict[str, Any],
    *,
    user_rpe: int,
) -> dict[str, Any]:
    """
    Aggregiert die Klassifikation eines Workouts.

    Die Ergebnisse können direkt angezeigt und später
    als JSON in Google Sheets gespeichert werden.
    """

    intensity_factor = max(
        0.1,
        min(1.0, user_rpe / 10),
    )

    movement_pattern_load: dict[str, float] = {}
    muscle_group_load: dict[str, float] = {}
    training_goal_counts: dict[str, int] = {}
    load_type_load: dict[str, float] = {}
    volume_totals: dict[str, float] = {}
    review_required: list[str] = []

    exercises = classified_workout.get(
        "uebungen",
        [],
    )

    if not isinstance(exercises, list):
        exercises = []

    for exercise in exercises:
        if not isinstance(exercise, dict):
            continue

        confidence = safely_convert_to_float(
            exercise.get(
                "overall_confidence"
            ),
            default=0.5,
        )

        if confidence is None:
            confidence = 0.5

        confidence_factor = max(
            0.25,
            min(1.0, confidence),
        )

        exercise_factor = (
            intensity_factor
            * confidence_factor
        )

        _aggregate_movement_patterns(
            exercise=exercise,
            target=movement_pattern_load,
            exercise_factor=exercise_factor,
        )

        _aggregate_muscle_groups(
            exercise=exercise,
            target=muscle_group_load,
            exercise_factor=exercise_factor,
        )

        _aggregate_training_goal(
            exercise=exercise,
            target=training_goal_counts,
        )

        _aggregate_load_types(
            exercise=exercise,
            target=load_type_load,
            exercise_factor=exercise_factor,
        )

        _aggregate_volume(
            exercise=exercise,
            target=volume_totals,
        )

        if exercise.get(
            "review_status"
        ) != "approved":
            exercise_name = (
                exercise.get(
                    "canonical_name"
                )
                or exercise.get("name")
                or "Unbekannte Übung"
            )

            review_required.append(
                str(exercise_name)
            )

    return {
        "movement_pattern_load": (
            movement_pattern_load
        ),
        "muscle_group_load": (
            muscle_group_load
        ),
        "training_goal_counts": (
            training_goal_counts
        ),
        "load_type_load": (
            load_type_load
        ),
        "volume_totals": (
            volume_totals
        ),
        "review_required": (
            review_required
        ),
    }


def _aggregate_movement_patterns(
    *,
    exercise: dict[str, Any],
    target: dict[str, float],
    exercise_factor: float,
) -> None:
    patterns = exercise.get(
        "movement_patterns",
        [],
    )

    if not isinstance(patterns, list):
        return

    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        pattern_type = pattern.get("type")

        contribution = safely_convert_to_float(
            pattern.get(
                "contribution"
            ),
            default=0.0,
        )

        if (
            not pattern_type
            or contribution is None
        ):
            continue

        target[pattern_type] = round(
            target.get(
                pattern_type,
                0.0,
            )
            + contribution
            * exercise_factor,
            3,
        )


def _aggregate_muscle_groups(
    *,
    exercise: dict[str, Any],
    target: dict[str, float],
    exercise_factor: float,
) -> None:
    muscles = exercise.get(
        "muscle_groups",
        [],
    )

    if not isinstance(muscles, list):
        return

    for muscle in muscles:
        if not isinstance(muscle, dict):
            continue

        muscle_type = muscle.get("type")

        contribution = safely_convert_to_float(
            muscle.get(
                "contribution"
            ),
            default=0.0,
        )

        if (
            not muscle_type
            or contribution is None
        ):
            continue

        target[muscle_type] = round(
            target.get(
                muscle_type,
                0.0,
            )
            + contribution
            * exercise_factor,
            3,
        )


def _aggregate_training_goal(
    *,
    exercise: dict[str, Any],
    target: dict[str, int],
) -> None:
    training_goal = exercise.get(
        "training_goal",
        {},
    )

    if not isinstance(
        training_goal,
        dict,
    ):
        return

    goal_type = training_goal.get(
        "type"
    )

    if not goal_type:
        return

    target[goal_type] = (
        target.get(goal_type, 0)
        + 1
    )


def _aggregate_load_types(
    *,
    exercise: dict[str, Any],
    target: dict[str, float],
    exercise_factor: float,
) -> None:
    load_types = exercise.get(
        "load_types",
        [],
    )

    if not isinstance(load_types, list):
        return

    for load_type in load_types:
        if not isinstance(
            load_type,
            dict,
        ):
            continue

        load_name = load_type.get("type")

        weight = safely_convert_to_float(
            load_type.get("weight"),
            default=0.0,
        )

        if (
            not load_name
            or weight is None
        ):
            continue

        target[load_name] = round(
            target.get(
                load_name,
                0.0,
            )
            + weight
            * exercise_factor,
            3,
        )


def _aggregate_volume(
    *,
    exercise: dict[str, Any],
    target: dict[str, float],
) -> None:
    volume = exercise.get(
        "volume",
        {},
    )

    if not isinstance(volume, dict):
        return

    for metric, value in volume.items():
        numeric_value = (
            safely_convert_to_float(
                value,
                default=None,
            )
        )

        if numeric_value is None:
            continue

        target[metric] = round(
            target.get(
                metric,
                0.0,
            )
            + numeric_value,
            2,
        )
