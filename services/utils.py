import hashlib
import json
import re
from typing import Any

import pandas as pd

from models.parsed_workout import ParsedWorkout


def create_stable_hash(data: dict[str, Any]) -> str:
    """
    Erzeugt einen reproduzierbaren SHA-256-Hash aus
    strukturierten Daten.
    """

    serialized = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def safely_convert_to_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    Konvertiert Pandas-, NumPy- und String-Werte sicher
    in einen Integer.
    """

    try:
        if value is None or pd.isna(value):
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


def safely_convert_to_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    """
    Konvertiert Werte sicher in eine Fließkommazahl.
    """

    try:
        if value is None or pd.isna(value):
            return default

        if isinstance(value, str) and not value.strip():
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def format_workout_as_text(
    exercises: list[dict[str, Any]],
) -> str:
    """
    Wandelt strukturierte Übungen in einen lesbaren Text
    für Google Sheets um.
    """

    workout_parts: list[str] = []

def format_workout_as_text(
    parsed_workout: ParsedWorkout,
) -> str:
    """
    Wandelt ein ParsedWorkout in einen lesbaren Text
    für Google Sheets und die Trainingshistorie um.
    """

    workout_parts: list[str] = []

    for segment in parsed_workout.segments:
        segment_parts: list[str] = []

        for element in segment.elements:
            name = str(
                element.movement.raw_name
                or element.movement.canonical_name
                or "Unbekannte Übung"
            ).strip()

            details: list[str] = []

            if element.sets is not None:
                details.append(
                    f"{element.sets} Sätze"
                )

            if element.reps is not None:
                details.append(
                    f"{element.reps} Wdh."
                )

            if element.distance is not None:
                distance_text = (
                    f"{element.distance:g}"
                )

                if element.distance_unit:
                    distance_text += (
                        f" {element.distance_unit}"
                    )

                details.append(distance_text)

            if element.duration is not None:
                duration_text = (
                    f"{element.duration:g}"
                )

                if element.duration_unit:
                    duration_text += (
                        f" {element.duration_unit}"
                    )

                details.append(duration_text)

            if element.calories is not None:
                details.append(
                    f"{element.calories} cal"
                )

            intensity = element.intensity

            if intensity.weight is not None:
                weight_text = (
                    f"{intensity.weight:g}"
                )

                if intensity.weight_unit:
                    weight_text += (
                        f" {intensity.weight_unit}"
                    )

                details.append(weight_text)

            if intensity.percent_1rm is not None:
                details.append(
                    f"{intensity.percent_1rm:g} % 1RM"
                )

            if intensity.prescribed_rpe is not None:
                details.append(
                    f"RPE {intensity.prescribed_rpe:g}"
                )

            if intensity.rir is not None:
                details.append(
                    f"RIR {intensity.rir}"
                )

            if intensity.tempo:
                details.append(
                    f"Tempo {intensity.tempo}"
                )

            if element.notes:
                details.append(
                    str(element.notes).strip()
                )

            if details:
                segment_parts.append(
                    f"{name}: {', '.join(details)}"
                )
            else:
                segment_parts.append(name)

        if not segment_parts:
            continue

        segment_label = str(
            segment.name
            or segment.type
            or ""
        ).strip()

        segment_details: list[str] = []

        if segment.rounds is not None:
            segment_details.append(
                f"{segment.rounds} Runden"
            )

        if segment.time_cap_minutes is not None:
            segment_details.append(
                f"Time Cap {segment.time_cap_minutes} Min."
            )

        if segment_label:
            prefix = segment_label

            if segment_details:
                prefix += (
                    f" ({', '.join(segment_details)})"
                )

            workout_parts.append(
                f"{prefix}: "
                + "; ".join(segment_parts)
            )
        else:
            workout_parts.append(
                "; ".join(segment_parts)
            )

    return " | ".join(workout_parts)


def clean_json_response(
    content: Any,
) -> dict[str, Any]:
    """
    Bereinigt eine Mistral-Antwort und liest sie als JSON.

    Unterstützt:
    - reines JSON,
    - Markdown-Codeblöcke,
    - zusätzlichen Text vor oder nach dem JSON,
    - JavaScript-artige //-Kommentare außerhalb von Strings.
    """

    if isinstance(content, dict):
        return content

    if not isinstance(content, str):
        raise ValueError(
            "Die KI-Antwort ist weder Text noch "
            "ein Dictionary."
        )

    cleaned = content.strip()

    if not cleaned:
        raise ValueError(
            "Die KI-Antwort ist leer."
        )

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    cleaned = _remove_json_line_comments(
        cleaned
    )

    try:
        parsed = json.loads(cleaned)

    except json.JSONDecodeError:
        parsed = _extract_json_object(
            cleaned
        )

    if not isinstance(parsed, dict):
        raise ValueError(
            "Das oberste JSON-Element muss "
            "ein Objekt sein."
        )

    return parsed


def _remove_json_line_comments(
    content: str,
) -> str:
    """
    Entfernt //-Kommentare außerhalb von JSON-Strings.

    Zeichenfolgen wie https:// innerhalb eines Strings
    bleiben erhalten.
    """

    result: list[str] = []
    index = 0
    inside_string = False
    escape_next = False

    while index < len(content):
        character = content[index]

        if escape_next:
            result.append(character)
            escape_next = False
            index += 1
            continue

        if (
            character == "\\"
            and inside_string
        ):
            result.append(character)
            escape_next = True
            index += 1
            continue

        if character == '"':
            inside_string = not inside_string
            result.append(character)
            index += 1
            continue

        if (
            not inside_string
            and character == "/"
            and index + 1 < len(content)
            and content[index + 1] == "/"
        ):
            index += 2

            while (
                index < len(content)
                and content[index]
                not in "\r\n"
            ):
                index += 1

            continue

        result.append(character)
        index += 1

    return "".join(result)



def _extract_json_object(
    content: str,
) -> dict[str, Any]:
    """
    Sucht das erste vollständige JSON-Objekt in einem
    Text. Geschweifte Klammern innerhalb von Strings
    werden korrekt berücksichtigt.
    """

    start_index = content.find("{")

    if start_index == -1:
        raise ValueError(
            "Die KI-Antwort enthält kein "
            "JSON-Objekt."
        )

    depth = 0
    inside_string = False
    escape_next = False

    for index in range(
        start_index,
        len(content),
    ):
        character = content[index]

        if escape_next:
            escape_next = False
            continue

        if (
            character == "\\"
            and inside_string
        ):
            escape_next = True
            continue

        if character == '"':
            inside_string = not inside_string
            continue

        if inside_string:
            continue

        if character == "{":
            depth += 1

        elif character == "}":
            depth -= 1

            if depth == 0:
                json_text = content[
                    start_index:index + 1
                ]

                try:
                    parsed = json.loads(
                        json_text
                    )

                except json.JSONDecodeError as error:
                    raise ValueError(
                        "Die KI-Antwort enthält ein "
                        "JSON-Objekt, dieses ist aber "
                        "syntaktisch ungültig."
                    ) from error

                if not isinstance(
                    parsed,
                    dict,
                ):
                    raise ValueError(
                        "Das erkannte JSON ist "
                        "kein Objekt."
                    )

                return parsed

    raise ValueError(
        "Das JSON-Objekt in der KI-Antwort "
        "ist unvollständig."
    )



def clamp(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    """
    Begrenzt einen Zahlenwert auf einen vorgegebenen
    Wertebereich.
    """

    numeric = safely_convert_to_float(
        value,
        default=minimum,
    )

    if numeric is None:
        numeric = minimum

    return max(
        minimum,
        min(maximum, numeric),
    )


def normalize_classification(
    data: dict[str, Any],
    *,
    movement_patterns: list[str],
    muscle_groups: list[str],
    training_goals: list[str],
    load_types: list[str],
    volume_metrics: list[str],
) -> dict[str, Any]:
    """
    Prüft und normalisiert die Workout-Klassifikation.

    Unbekannte Kategorien werden entfernt. Konfidenz-
    und Beteiligungswerte werden auf 0 bis 1 begrenzt.
    """

    normalized_exercises: list[dict[str, Any]] = []

    raw_exercises = data.get("uebungen", [])

    if not isinstance(raw_exercises, list):
        raw_exercises = []

    for raw_exercise in raw_exercises:
        if not isinstance(raw_exercise, dict):
            continue

        normalized_patterns: list[dict[str, Any]] = []

        raw_patterns = raw_exercise.get(
            "movement_patterns",
            [],
        )

        if not isinstance(raw_patterns, list):
            raw_patterns = []

        for item in raw_patterns:
            if not isinstance(item, dict):
                continue

            pattern_type = item.get("type")
            role = item.get("role")

            if pattern_type not in movement_patterns:
                continue

            if role not in [
                "primary",
                "secondary",
            ]:
                continue

            normalized_patterns.append(
                {
                    "type": pattern_type,
                    "role": role,
                    "contribution": clamp(
                        item.get("contribution")
                    ),
                }
            )

        primary_patterns = [
            item
            for item in normalized_patterns
            if item["role"] == "primary"
        ]

        ambiguity_reason = raw_exercise.get(
            "ambiguity_reason"
        )

        if len(primary_patterns) != 1:
            ambiguity_reason = (
                "Kein eindeutiges primäres "
                "Bewegungsmuster erkannt."
            )

        normalized_muscles: list[dict[str, Any]] = []

        raw_muscles = raw_exercise.get(
            "muscle_groups",
            [],
        )

        if not isinstance(raw_muscles, list):
            raw_muscles = []

        for item in raw_muscles:
            if not isinstance(item, dict):
                continue

            muscle_type = item.get("type")
            role = item.get("role")

            if muscle_type not in muscle_groups:
                continue

            if role not in [
                "primary",
                "secondary",
                "stabilizer",
            ]:
                continue

            normalized_muscles.append(
                {
                    "type": muscle_type,
                    "role": role,
                    "contribution": clamp(
                        item.get("contribution")
                    ),
                }
            )

        normalized_load_types: list[dict[str, Any]] = []

        raw_load_types = raw_exercise.get(
            "load_types",
            [],
        )

        if not isinstance(raw_load_types, list):
            raw_load_types = []

        for item in raw_load_types:
            if not isinstance(item, dict):
                continue

            load_type = item.get("type")

            if load_type not in load_types:
                continue

            normalized_load_types.append(
                {
                    "type": load_type,
                    "weight": clamp(
                        item.get("weight")
                    ),
                }
            )

        raw_goal = raw_exercise.get(
            "training_goal",
            {},
        )

        if not isinstance(raw_goal, dict):
            raw_goal = {}

        goal_type = raw_goal.get("type")

        if goal_type not in training_goals:
            goal_type = None

        raw_supported_metrics = raw_exercise.get(
            "supported_volume_metrics",
            [],
        )

        if not isinstance(raw_supported_metrics, list):
            raw_supported_metrics = []

        supported_metrics = [
            metric
            for metric in raw_supported_metrics
            if metric in volume_metrics
        ]

        raw_volume = raw_exercise.get(
            "volume",
            {},
        )

        if not isinstance(raw_volume, dict):
            raw_volume = {}

        normalized_volume = {
            metric: safely_convert_to_float(
                raw_volume.get(metric),
                default=None,
            )
            for metric in volume_metrics
        }

        overall_confidence = clamp(
            raw_exercise.get(
                "overall_confidence"
            )
        )

        if ambiguity_reason or overall_confidence < 0.7:
            review_status = "needs_review"

        elif overall_confidence < 0.9:
            review_status = "flagged"

        else:
            review_status = "approved"

        notes = raw_exercise.get("notes", [])

        if not isinstance(notes, list):
            notes = []

        normalized_exercises.append(
            {
                "name": str(
                    raw_exercise.get(
                        "name",
                        "",
                    )
                ).strip(),
                "details": str(
                    raw_exercise.get(
                        "details",
                        "",
                    )
                ).strip(),
                "canonical_name": str(
                    raw_exercise.get(
                        "canonical_name",
                        "",
                    )
                ).strip(),
                "canonical_id": str(
                    raw_exercise.get(
                        "canonical_id",
                        "",
                    )
                ).strip(),
                "movement_patterns": normalized_patterns,
                "muscle_groups": normalized_muscles,
                "training_goal": {
                    "type": goal_type,
                    "confidence": clamp(
                        raw_goal.get("confidence")
                    ),
                    "reason": str(
                        raw_goal.get(
                            "reason",
                            "",
                        )
                    ).strip(),
                },
                "load_types": normalized_load_types,
                "volume": normalized_volume,
                "supported_volume_metrics": supported_metrics,
                "overall_confidence": overall_confidence,
                "ambiguity_reason": (
                    str(ambiguity_reason).strip()
                    if ambiguity_reason
                    else None
                ),
                "notes": [
                    str(note).strip()
                    for note in notes
                    if str(note).strip()
                ][:5],
                "review_status": review_status,
            }
        )

    return {
        "workout_erkannt": bool(
            data.get(
                "workout_erkannt",
                True,
            )
        ),
        "uebungen": normalized_exercises,
    }


def json_dumps_for_sheet(
    value: Any,
) -> str:
    """
    Wandelt Dictionaries oder Listen in kompakten
    JSON-Text für Google Sheets um.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def json_loads_from_sheet(
    value: Any,
    default: Any = None,
) -> Any:
    """
    Liest JSON aus einer Google-Sheets-Zelle.
    """

    if default is None:
        default = {}

    if isinstance(value, (dict, list)):
        return value

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return default

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        return default