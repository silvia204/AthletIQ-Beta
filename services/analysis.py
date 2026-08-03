from __future__ import annotations

from typing import Any


SEVERITY_WEIGHTS = {
    "low": 20,
    "medium": 50,
    "high": 75,
    "critical": 95,
}


GOAL_ALIASES = {
    "crossfit": "crossfit",
    "hyrox": "hyrox",
    "general_fitness": "general_fitness",
    "general fitness": "general_fitness",
    "abnehmen": "fat_loss",
    "fat_loss": "fat_loss",
    "fat loss": "fat_loss",
}

# Multiplikatoren werden nur auf die Priorisierung angewendet.
# Die objektive Finding-Erzeugung bleibt für alle Ziele identisch.
GOAL_CATEGORY_WEIGHTS = {
    "crossfit": {
        "recovery": 1.15,
        "training_load": 1.10,
        "movement_pattern": 1.10,
        "muscle_group": 1.05,
        "training_goal": 1.00,
    },
    "hyrox": {
        "recovery": 1.20,
        "training_load": 1.15,
        "movement_pattern": 1.05,
        "muscle_group": 1.05,
        "training_goal": 1.10,
    },
    "general_fitness": {
        "recovery": 1.20,
        "training_load": 1.10,
        "movement_pattern": 1.10,
        "muscle_group": 1.10,
        "training_goal": 0.95,
    },
    "fat_loss": {
        "recovery": 1.20,
        "training_load": 1.10,
        "movement_pattern": 1.00,
        "muscle_group": 1.00,
        "training_goal": 1.10,
    },
}

GOAL_CODE_WEIGHTS = {
    "crossfit": {
        "missing_goal_aerobic_base": 1.15,
        "goal_aerobic_base_not_recent": 1.15,
        "missing_vertical_pull": 1.20,
        "vertical_pull_not_recent": 1.20,
        "missing_horizontal_pull": 1.15,
        "horizontal_pull_not_recent": 1.15,
        "missing_hinge": 1.15,
        "hinge_not_recent": 1.15,
    },
    "hyrox": {
        "missing_goal_aerobic_base": 1.35,
        "goal_aerobic_base_not_recent": 1.35,
        "missing_goal_threshold": 1.30,
        "goal_threshold_not_recent": 1.30,
        "missing_goal_vo2max": 1.20,
        "goal_vo2max_not_recent": 1.20,
        "missing_locomotion": 1.35,
        "locomotion_not_recent": 1.35,
        "missing_carry": 1.25,
        "carry_not_recent": 1.25,
        "forearms_grip_not_recent": 1.15,
        "missing_hinge": 1.10,
        "hinge_not_recent": 1.10,
    },
    "general_fitness": {
        "missing_goal_aerobic_base": 1.20,
        "goal_aerobic_base_not_recent": 1.20,
        "missing_goal_mobility": 1.20,
        "goal_mobility_not_recent": 1.20,
        "missing_goal_recovery": 1.20,
        "goal_recovery_not_recent": 1.20,
        "missing_goal_technique": 0.85,
        "goal_technique_not_recent": 0.85,
        "missing_goal_explosive_strength": 0.70,
        "goal_explosive_strength_not_recent": 0.70,
        "missing_goal_speed_strength": 0.75,
        "goal_speed_strength_not_recent": 0.75,
    },
    "fat_loss": {
        "missing_goal_aerobic_base": 1.35,
        "goal_aerobic_base_not_recent": 1.35,
        "missing_goal_recovery": 1.20,
        "goal_recovery_not_recent": 1.20,
        "insufficient_easy_sessions": 1.25,
        "high_density_without_easy_session": 1.25,
        "limited_recovery_distribution": 1.20,
        "missing_goal_max_strength": 1.05,
        "goal_max_strength_not_recent": 1.05,
        "missing_goal_explosive_strength": 0.65,
        "goal_explosive_strength_not_recent": 0.65,
        "missing_goal_speed_strength": 0.65,
        "goal_speed_strength_not_recent": 0.65,
    },
}

GOAL_IGNORED_CODES = {
    "general_fitness": {
        "missing_goal_explosive_strength",
        "goal_explosive_strength_not_recent",
        "missing_goal_speed_strength",
        "goal_speed_strength_not_recent",
    },
    "fat_loss": {
        "missing_goal_explosive_strength",
        "goal_explosive_strength_not_recent",
        "missing_goal_speed_strength",
        "goal_speed_strength_not_recent",
    },
}


def safely_get_dict(
    value: Any,
) -> dict[str, Any]:
    """
    Gibt nur echte Dictionaries zurück.

    Dadurch bleiben die Analysefunktionen stabil, wenn
    Daten fehlen oder ältere Historieneinträge noch keine
    strukturierten Trainingsdimensionen enthalten.
    """

    if isinstance(value, dict):
        return value

    return {}


def safely_get_list(
    value: Any,
) -> list[Any]:
    """
    Gibt nur echte Listen zurück.
    """

    if isinstance(value, list):
        return value

    return []


def safely_get_float(
    value: Any,
    *,
    default: float = 0.0,
) -> float:
    """
    Konvertiert einen Wert robust in float.
    """

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def safely_get_int(
    value: Any,
    *,
    default: int = 0,
) -> int:
    """
    Konvertiert einen Wert robust in int.
    """

    try:
        if value is None:
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Begrenzung eines numerischen Wertes.
    """

    return max(
        minimum,
        min(maximum, value),
    )


def normalize_dimension_name(
    value: str,
) -> str:
    """
    Normalisiert Dimensionsnamen für stabile Codes.
    """

    normalized = (
        str(value)
        .strip()
        .casefold()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )

    while "__" in normalized:
        normalized = normalized.replace(
            "__",
            "_",
        )

    return normalized.strip("_")


def calculate_impact_score(
    *,
    severity: str,
    confidence: float = 1.0,
    magnitude: float = 1.0,
    recency: float = 1.0,
) -> int:
    """
    Berechnet einen priorisierbaren Impact-Score.

    severity:
        Grundgewicht des Findings.

    confidence:
        Qualität bzw. Vollständigkeit der Evidenz.

    magnitude:
        Stärke der Abweichung.

    recency:
        Relevanz der zeitlichen Nähe.

    Alle Faktoren außer severity werden zwischen
    0.0 und 1.5 begrenzt.
    """

    base_score = SEVERITY_WEIGHTS.get(
        severity,
        SEVERITY_WEIGHTS["medium"],
    )

    confidence_factor = clamp(
        confidence,
        0.0,
        1.5,
    )

    magnitude_factor = clamp(
        magnitude,
        0.0,
        1.5,
    )

    recency_factor = clamp(
        recency,
        0.0,
        1.5,
    )

    weighted_score = (
        base_score
        * confidence_factor
        * (
            0.65
            + 0.20 * magnitude_factor
            + 0.15 * recency_factor
        )
    )

    return int(
        round(
            clamp(
                weighted_score,
                0,
                100,
            )
        )
    )


def create_finding(
    *,
    finding_type: str,
    severity: str,
    category: str,
    code: str,
    title: str,
    description: str,
    recommendation: str,
    evidence: dict[str, Any] | None = None,
    confidence: float = 1.0,
    magnitude: float = 1.0,
    recency: float = 1.0,
) -> dict[str, Any]:
    """
    Erstellt ein Finding im einheitlichen Datenformat.
    """

    normalized_code = normalize_dimension_name(
        code
    )

    impact_score = calculate_impact_score(
        severity=severity,
        confidence=confidence,
        magnitude=magnitude,
        recency=recency,
    )

    return {
        "type": finding_type,
        "severity": severity,
        "category": category,
        "code": normalized_code,
        "title": title,
        "description": description,
        "recommendation": recommendation,
        "impact_score": impact_score,
        "confidence": round(
            clamp(confidence, 0.0, 1.0),
            2,
        ),
        "evidence": evidence or {},
    }


def get_window(
    history_summary: dict[str, Any],
    window_name: str,
) -> dict[str, Any]:
    """
    Liest ein Analysezeitfenster robust aus.
    """

    windows = safely_get_dict(
        history_summary.get("windows")
    )

    return safely_get_dict(
        windows.get(window_name)
    )


def get_dimension(
    window: dict[str, Any],
    dimension_name: str,
) -> dict[str, Any]:
    """
    Liest eine aggregierte Trainingsdimension aus.
    """

    return safely_get_dict(
        window.get(dimension_name)
    )


def analyze_balance(
    history_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Analysiert das Verhältnis funktionell verwandter
    Muskelgruppen und Bewegungsmuster.

    Die Funktion verwendet primär das 28-Tage-Fenster,
    damit einzelne Wochen nicht überbewertet werden.
    """

    findings: list[dict[str, Any]] = []

    window_28 = get_window(
        history_summary,
        "28_days",
    )

    sessions_28 = safely_get_int(
        window_28.get("sessions")
    )

    if sessions_28 < 4:
        return findings

    muscle_load = get_dimension(
        window_28,
        "muscle_group_load",
    )

    movement_load = get_dimension(
        window_28,
        "movement_pattern_load",
    )

    muscle_pairs = [
        {
            "primary": "quadriceps",
            "counterpart": "hamstrings",
            "title": "Balance Vorder- und Rückseite der Beine",
            "recommendation": (
                "Ergänze bei der nächsten passenden "
                "Krafteinheit eine hüftdominante oder "
                "hamstringbetonte Übung."
            ),
        },
        {
            "primary": "chest",
            "counterpart": "latissimus",
            "title": "Balance Drücken und Ziehen",
            "recommendation": (
                "Ergänze horizontale oder vertikale "
                "Zugbewegungen, um das Druckvolumen "
                "auszugleichen."
            ),
        },
        {
            "primary": "front_delts",
            "counterpart": "rear_delts",
            "title": "Balance der Schultermuskulatur",
            "recommendation": (
                "Plane gezielte Arbeit für hintere "
                "Schulter und Schulterblattkontrolle ein."
            ),
        },
    ]

    for pair in muscle_pairs:
        primary_name = pair["primary"]
        counterpart_name = pair[
            "counterpart"
        ]

        primary_load = safely_get_float(
            muscle_load.get(primary_name)
        )

        counterpart_load = safely_get_float(
            muscle_load.get(
                counterpart_name
            )
        )

        if primary_load < 2.0:
            continue

        if counterpart_load <= 0:
            ratio = None
            severity = "high"
            magnitude = 1.4

        else:
            ratio = (
                primary_load
                / counterpart_load
            )

            if ratio < 2.0:
                continue

            severity = (
                "high"
                if ratio >= 3.5
                else "medium"
            )

            magnitude = clamp(
                ratio / 3.0,
                0.8,
                1.5,
            )

        counterpart_label = (
            counterpart_name.replace(
                "_",
                " ",
            )
        )

        primary_label = (
            primary_name.replace(
                "_",
                " ",
            )
        )

        description = (
            f"„{primary_label}“ wurde im "
            "28-Tage-Zeitraum deutlich stärker "
            f"belastet als „{counterpart_label}“."
        )

        findings.append(
            create_finding(
                finding_type="imbalance",
                severity=severity,
                category="muscle_group",
                code=(
                    f"imbalance_{primary_name}"
                    f"_to_{counterpart_name}"
                ),
                title=pair["title"],
                description=description,
                recommendation=pair[
                    "recommendation"
                ],
                evidence={
                    "window_days": 28,
                    "primary": primary_name,
                    "primary_load": (
                        round(
                            primary_load,
                            2,
                        )
                    ),
                    "counterpart": (
                        counterpart_name
                    ),
                    "counterpart_load": (
                        round(
                            counterpart_load,
                            2,
                        )
                    ),
                    "ratio": (
                        round(ratio, 2)
                        if ratio is not None
                        else None
                    ),
                    "sessions": sessions_28,
                },
                confidence=(
                    1.0
                    if sessions_28 >= 8
                    else 0.8
                ),
                magnitude=magnitude,
            )
        )

    movement_pairs = [
        {
            "primary": "horizontal_push",
            "counterpart": "horizontal_pull",
            "title": "Horizontale Push-Pull-Balance",
            "recommendation": (
                "Ergänze Rudervarianten oder reduziere "
                "vorübergehend horizontales Drücken."
            ),
        },
        {
            "primary": "vertical_push",
            "counterpart": "vertical_pull",
            "title": "Vertikale Push-Pull-Balance",
            "recommendation": (
                "Ergänze Klimmzüge, unterstützte "
                "Klimmzüge oder Latziehen."
            ),
        },
        {
            "primary": "squat",
            "counterpart": "hinge",
            "title": "Knie- und Hüftdominanz",
            "recommendation": (
                "Ergänze eine hüftdominante Bewegung "
                "wie RDL, Deadlift oder Hip Hinge."
            ),
        },
    ]

    for pair in movement_pairs:
        primary_name = pair["primary"]
        counterpart_name = pair[
            "counterpart"
        ]

        primary_load = safely_get_float(
            movement_load.get(primary_name)
        )

        counterpart_load = safely_get_float(
            movement_load.get(
                counterpart_name
            )
        )

        if primary_load < 2.0:
            continue

        if counterpart_load <= 0:
            ratio = None
            severity = "high"
            magnitude = 1.4

        else:
            ratio = (
                primary_load
                / counterpart_load
            )

            if ratio < 2.25:
                continue

            severity = (
                "high"
                if ratio >= 4.0
                else "medium"
            )

            magnitude = clamp(
                ratio / 3.5,
                0.8,
                1.5,
            )

        findings.append(
            create_finding(
                finding_type="imbalance",
                severity=severity,
                category=(
                    "movement_pattern"
                ),
                code=(
                    f"imbalance_{primary_name}"
                    f"_to_{counterpart_name}"
                ),
                title=pair["title"],
                description=(
                    f"Das Bewegungsmuster "
                    f"„{primary_name}“ war im "
                    "28-Tage-Zeitraum deutlich "
                    f"stärker vertreten als "
                    f"„{counterpart_name}“."
                ),
                recommendation=pair[
                    "recommendation"
                ],
                evidence={
                    "window_days": 28,
                    "primary": primary_name,
                    "primary_load": round(
                        primary_load,
                        2,
                    ),
                    "counterpart": (
                        counterpart_name
                    ),
                    "counterpart_load": round(
                        counterpart_load,
                        2,
                    ),
                    "ratio": (
                        round(ratio, 2)
                        if ratio is not None
                        else None
                    ),
                    "sessions": sessions_28,
                },
                confidence=(
                    1.0
                    if sessions_28 >= 8
                    else 0.8
                ),
                magnitude=magnitude,
            )
        )

    return findings


def analyze_overload(
    history_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Wandelt objektive Überlastungswarnsignale aus
    history.py in standardisierte Findings um.
    """

    findings: list[dict[str, Any]] = []

    raw_signals = safely_get_list(
        history_summary.get(
            "overload_signals"
        )
    )

    window_7 = get_window(
        history_summary,
        "7_days",
    )

    sessions_7 = safely_get_int(
        window_7.get("sessions")
    )

    average_rpe_7 = window_7.get(
        "average_rpe"
    )

    high_rpe_sessions = safely_get_int(
        window_7.get(
            "high_rpe_sessions"
        )
    )

    total_score_7 = safely_get_float(
        window_7.get("total_score")
    )

    severity_mapping = {
        "notice": "medium",
        "warning": "high",
        "critical": "critical",
    }

    title_mapping = {
        "rapid_weekly_load_increase": (
            "Schneller Belastungsanstieg"
        ),
        "repeated_high_rpe": (
            "Mehrere intensive Einheiten"
        ),
        "repeated_very_high_rpe": (
            "Wiederholt sehr hohe Intensität"
        ),
        "insufficient_easy_sessions": (
            "Wenig regenerative Belastung"
        ),
        "high_mechanical_load": (
            "Hohe mechanische Belastung"
        ),
        "high_eccentric_load": (
            "Hohe exzentrische Belastung"
        ),
        "high_impact_load": (
            "Hohe Stoßbelastung"
        ),
        "high_neuromuscular_load": (
            "Hohe neuromuskuläre Belastung"
        ),
    }

    recommendation_mapping = {
        "rapid_weekly_load_increase": (
            "Vermeide einen weiteren deutlichen "
            "Belastungssprung und plane die nächste "
            "Einheit kontrolliert."
        ),
        "repeated_high_rpe": (
            "Plane eine leichtere Einheit oder reduziere "
            "Volumen und Intensität."
        ),
        "repeated_very_high_rpe": (
            "Priorisiere Erholung und vermeide eine "
            "weitere maximale Einheit ohne ausreichenden "
            "Abstand."
        ),
        "insufficient_easy_sessions": (
            "Ergänze eine lockere aerobe, technische "
            "oder regenerative Einheit."
        ),
        "high_mechanical_load": (
            "Reduziere bei Bedarf externe Last, Volumen "
            "oder die Anzahl schwerer Wiederholungen."
        ),
        "high_eccentric_load": (
            "Plane ausreichend Abstand vor der nächsten "
            "stark exzentrischen Belastung."
        ),
        "high_impact_load": (
            "Reduziere vorübergehend Sprung-, Lauf- oder "
            "Stoßvolumen, falls Ermüdung besteht."
        ),
        "high_neuromuscular_load": (
            "Plane vor der nächsten explosiven oder "
            "maximalen Einheit ausreichend Erholung."
        ),
    }

    for signal in raw_signals:
        if not isinstance(signal, dict):
            continue

        code = normalize_dimension_name(
            signal.get(
                "code",
                "unknown_overload_signal",
            )
        )

        raw_severity = str(
            signal.get(
                "severity",
                "notice",
            )
        ).casefold()

        severity = severity_mapping.get(
            raw_severity,
            "medium",
        )

        if (
            code.startswith("high_recent_")
            and code.endswith("_load")
        ):
            dimension = (
                code.removeprefix(
                    "high_recent_"
                )
                .removesuffix("_load")
            )

            dimension_label = (
                dimension.replace(
                    "_",
                    " ",
                ).title()
            )

            title = (
                "Hohe wiederholte Belastung: "
                f"{dimension_label}"
            )

            recommendation = (
                "Berücksichtige die wiederholte "
                "Belastung dieser Muskelgruppe bei "
                "der Planung der nächsten Einheit."
            )

        else:
            title = title_mapping.get(
                code,
                code.replace(
                    "_",
                    " ",
                ).title(),
            )

            recommendation = (
                recommendation_mapping.get(
                    code,
                    (
                        "Prüfe Belastung, Erholung "
                        "und Einheitenplanung, bevor "
                        "die Belastung weiter erhöht "
                        "wird."
                    ),
                )
            )

        magnitude = (
            1.3
            if severity in {
                "high",
                "critical",
            }
            else 1.0
        )

        findings.append(
            create_finding(
                finding_type="overload",
                severity=severity,
                category="training_load",
                code=code,
                title=title,
                description=str(
                    signal.get(
                        "message",
                        "Erhöhte Belastung erkannt.",
                    )
                ),
                recommendation=(
                    recommendation
                ),
                evidence={
                    "window_days": 7,
                    "sessions": sessions_7,
                    "average_rpe": (
                        average_rpe_7
                    ),
                    "high_rpe_sessions": (
                        high_rpe_sessions
                    ),
                    "total_score": round(
                        total_score_7,
                        2,
                    ),
                    "source_signal": signal,
                },
                confidence=(
                    1.0
                    if sessions_7 >= 4
                    else 0.75
                ),
                magnitude=magnitude,
                recency=1.2,
            )
        )

    return findings


def analyze_undertraining(
    history_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Analysiert fehlende und länger nicht trainierte
    Bewegungsmuster, Muskelgruppen und Trainingsziele.
    """

    findings: list[dict[str, Any]] = []

    raw_signals = safely_get_list(
        history_summary.get(
            "undertraining_signals"
        )
    )

    window_28 = get_window(
        history_summary,
        "28_days",
    )

    sessions_28 = safely_get_int(
        window_28.get("sessions")
    )

    movement_load = get_dimension(
        window_28,
        "movement_pattern_load",
    )

    muscle_load = get_dimension(
        window_28,
        "muscle_group_load",
    )

    goal_counts = get_dimension(
        window_28,
        "training_goal_counts",
    )

    days_since = safely_get_dict(
        history_summary.get(
            "days_since_last_load"
        )
    )

    movement_days = safely_get_dict(
        days_since.get(
            "movement_patterns"
        )
    )

    muscle_days = safely_get_dict(
        days_since.get("muscle_groups")
    )

    goal_days = safely_get_dict(
        days_since.get("training_goals")
    )

    for signal in raw_signals:
        if not isinstance(signal, dict):
            continue

        code = normalize_dimension_name(
            signal.get(
                "code",
                "unknown_undertraining_signal",
            )
        )

        message = str(
            signal.get(
                "message",
                "Unterrepräsentierter Trainingsanteil.",
            )
        )

        severity = "medium"
        category = "training_dimension"
        title = (
            code.replace("_", " ").title()
        )
        recommendation = (
            "Ergänze den fehlenden Trainingsanteil "
            "progressiv in einer der nächsten Einheiten."
        )

        evidence: dict[str, Any] = {
            "window_days": 28,
            "sessions": sessions_28,
            "source_signal": signal,
        }

        if code.startswith("missing_goal_"):
            goal = code.removeprefix(
                "missing_goal_"
            )

            category = "training_goal"
            title = (
                f"Trainingsziel fehlt: "
                f"{goal.replace('_', ' ').title()}"
            )

            evidence.update(
                {
                    "training_goal": goal,
                    "count_28_days": (
                        safely_get_int(
                            goal_counts.get(goal)
                        )
                    ),
                    "days_since_last": (
                        goal_days.get(goal)
                    ),
                }
            )

            recommendation = (
                "Plane eine passende Einheit für "
                f"„{goal}“ ein, sofern dieses Ziel "
                "zum aktuellen Trainingsplan gehört."
            )

        elif code.startswith("goal_"):
            goal = (
                code.removeprefix("goal_")
                .removesuffix("_not_recent")
            )

            category = "training_goal"
            title = (
                f"Länger nicht trainiert: "
                f"{goal.replace('_', ' ').title()}"
            )

            days_value = safely_get_int(
                goal_days.get(goal)
            )

            evidence.update(
                {
                    "training_goal": goal,
                    "count_28_days": (
                        safely_get_int(
                            goal_counts.get(goal)
                        )
                    ),
                    "days_since_last": (
                        days_value
                    ),
                }
            )

            severity = (
                "high"
                if days_value >= 35
                else "medium"
            )

        elif code.startswith("missing_"):
            dimension = code.removeprefix(
                "missing_"
            )

            category = "movement_pattern"
            title = (
                "Fehlendes Bewegungsmuster: "
                f"{dimension.replace('_', ' ').title()}"
            )

            evidence.update(
                {
                    "movement_pattern": (
                        dimension
                    ),
                    "load_28_days": (
                        safely_get_float(
                            movement_load.get(
                                dimension
                            )
                        )
                    ),
                    "days_since_last": (
                        movement_days.get(
                            dimension
                        )
                    ),
                }
            )

            recommendation = (
                "Ergänze eine geeignete Übung für "
                f"„{dimension}“, sofern keine "
                "sportartspezifische oder medizinische "
                "Einschränkung dagegen spricht."
            )

        elif code.endswith("_not_recent"):
            dimension = code.removesuffix(
                "_not_recent"
            )

            if dimension in muscle_days:
                category = "muscle_group"
                title = (
                    "Muskelgruppe länger nicht belastet: "
                    f"{dimension.replace('_', ' ').title()}"
                )

                days_value = safely_get_int(
                    muscle_days.get(dimension)
                )

                evidence.update(
                    {
                        "muscle_group": dimension,
                        "load_28_days": (
                            safely_get_float(
                                muscle_load.get(
                                    dimension
                                )
                            )
                        ),
                        "days_since_last": (
                            days_value
                        ),
                    }
                )

                recommendation = (
                    "Integriere eine kontrollierte "
                    f"Belastung für „{dimension}“ in "
                    "eine der nächsten Einheiten."
                )

            else:
                category = (
                    "movement_pattern"
                )

                title = (
                    "Bewegungsmuster länger nicht "
                    "belastet: "
                    f"{dimension.replace('_', ' ').title()}"
                )

                days_value = safely_get_int(
                    movement_days.get(
                        dimension
                    )
                )

                evidence.update(
                    {
                        "movement_pattern": (
                            dimension
                        ),
                        "load_28_days": (
                            safely_get_float(
                                movement_load.get(
                                    dimension
                                )
                            )
                        ),
                        "days_since_last": (
                            days_value
                        ),
                    }
                )

            severity = (
                "high"
                if days_value >= 28
                else "medium"
            )

        days_without_load = safely_get_int(
            evidence.get("days_since_last")
        )

        magnitude = (
            clamp(
                days_without_load / 21,
                0.8,
                1.5,
            )
            if days_without_load > 0
            else 1.0
        )

        findings.append(
            create_finding(
                finding_type="undertraining",
                severity=severity,
                category=category,
                code=code,
                title=title,
                description=message,
                recommendation=(
                    recommendation
                ),
                evidence=evidence,
                confidence=(
                    1.0
                    if sessions_28 >= 8
                    else 0.75
                ),
                magnitude=magnitude,
                recency=1.0,
            )
        )

    return findings


def analyze_recovery(
    history_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Verknüpft Trainingsfrequenz, RPE und leichte Einheiten
    zu zusätzlichen Regenerationshinweisen.
    """

    findings: list[dict[str, Any]] = []

    window_7 = get_window(
        history_summary,
        "7_days",
    )

    sessions = safely_get_int(
        window_7.get("sessions")
    )

    average_rpe = window_7.get(
        "average_rpe"
    )

    average_rpe_numeric = safely_get_float(
        average_rpe
    )

    high_rpe_sessions = safely_get_int(
        window_7.get(
            "high_rpe_sessions"
        )
    )

    low_rpe_sessions = safely_get_int(
        window_7.get(
            "low_rpe_sessions"
        )
    )

    if (
        sessions >= 5
        and average_rpe_numeric >= 7.5
        and low_rpe_sessions == 0
    ):
        findings.append(
            create_finding(
                finding_type="recovery",
                severity="high",
                category="recovery",
                code=(
                    "high_density_without_easy_session"
                ),
                title=(
                    "Hohe Trainingsdichte ohne "
                    "leichte Einheit"
                ),
                description=(
                    f"In den letzten 7 Tagen wurden "
                    f"{sessions} Einheiten mit einer "
                    f"durchschnittlichen RPE von "
                    f"{average_rpe_numeric:.1f} "
                    "dokumentiert. Eine leichte "
                    "Einheit fehlt."
                ),
                recommendation=(
                    "Plane eine leichte, technische "
                    "oder regenerative Einheit ein und "
                    "vermeide einen weiteren maximalen "
                    "Belastungsreiz."
                ),
                evidence={
                    "window_days": 7,
                    "sessions": sessions,
                    "average_rpe": round(
                        average_rpe_numeric,
                        1,
                    ),
                    "high_rpe_sessions": (
                        high_rpe_sessions
                    ),
                    "low_rpe_sessions": (
                        low_rpe_sessions
                    ),
                },
                confidence=1.0,
                magnitude=1.3,
                recency=1.3,
            )
        )

    elif (
        sessions >= 4
        and high_rpe_sessions >= 3
        and low_rpe_sessions == 0
    ):
        findings.append(
            create_finding(
                finding_type="recovery",
                severity="medium",
                category="recovery",
                code=(
                    "limited_recovery_distribution"
                ),
                title=(
                    "Wenig Belastungsvariation"
                ),
                description=(
                    "Mehrere intensive Einheiten wurden "
                    "ohne dokumentierte leichte Einheit "
                    "absolviert."
                ),
                recommendation=(
                    "Verteile intensive und leichte "
                    "Belastungen deutlicher über die "
                    "Trainingswoche."
                ),
                evidence={
                    "window_days": 7,
                    "sessions": sessions,
                    "average_rpe": (
                        average_rpe
                    ),
                    "high_rpe_sessions": (
                        high_rpe_sessions
                    ),
                    "low_rpe_sessions": (
                        low_rpe_sessions
                    ),
                },
                confidence=0.9,
                magnitude=1.1,
                recency=1.2,
            )
        )

    return findings


def analyze_progression(
    history_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Analysiert kurzfristige Veränderungen der
    Trainingsbelastung.
    """

    findings: list[dict[str, Any]] = []

    current_load = safely_get_float(
        history_summary.get(
            "belastung_letzte_7_tage"
        )
    )

    previous_load = safely_get_float(
        history_summary.get(
            "belastung_vorherige_7_tage"
        )
    )

    change_value = history_summary.get(
        "belastungsveraenderung_prozent"
    )

    change_percent = (
        safely_get_float(change_value)
        if change_value is not None
        else None
    )

    window_7 = get_window(
        history_summary,
        "7_days",
    )

    sessions_7 = safely_get_int(
        window_7.get("sessions")
    )

    if (
        change_percent is not None
        and change_percent >= 30
        and sessions_7 >= 3
    ):
        severity = (
            "high"
            if change_percent >= 60
            else "medium"
        )

        findings.append(
            create_finding(
                finding_type="progression",
                severity=severity,
                category="training_load",
                code=(
                    "weekly_load_progression_high"
                ),
                title=(
                    "Deutlicher Belastungsanstieg"
                ),
                description=(
                    "Die dokumentierte Belastung der "
                    "letzten 7 Tage ist gegenüber den "
                    "vorherigen 7 Tagen um "
                    f"{change_percent:.1f} % gestiegen."
                ),
                recommendation=(
                    "Erhöhe die Belastung in der "
                    "kommenden Woche nicht erneut stark "
                    "und beobachte Ermüdung, Leistung "
                    "und Beschwerden."
                ),
                evidence={
                    "current_7_day_load": round(
                        current_load,
                        2,
                    ),
                    "previous_7_day_load": round(
                        previous_load,
                        2,
                    ),
                    "change_percent": round(
                        change_percent,
                        1,
                    ),
                    "sessions_7_days": (
                        sessions_7
                    ),
                },
                confidence=1.0,
                magnitude=clamp(
                    change_percent / 50,
                    0.8,
                    1.5,
                ),
                recency=1.3,
            )
        )

    elif (
        change_percent is not None
        and change_percent <= -50
        and previous_load > 0
    ):
        findings.append(
            create_finding(
                finding_type="progression",
                severity="low",
                category="training_load",
                code=(
                    "weekly_load_drop"
                ),
                title=(
                    "Deutlicher Belastungsrückgang"
                ),
                description=(
                    "Die dokumentierte Belastung der "
                    "letzten 7 Tage ist gegenüber der "
                    "Vorwoche um "
                    f"{abs(change_percent):.1f} % "
                    "gesunken."
                ),
                recommendation=(
                    "Prüfe, ob der Rückgang als "
                    "Regenerationsphase geplant war "
                    "oder ob wichtige Trainingsreize "
                    "ungeplant ausgefallen sind."
                ),
                evidence={
                    "current_7_day_load": round(
                        current_load,
                        2,
                    ),
                    "previous_7_day_load": round(
                        previous_load,
                        2,
                    ),
                    "change_percent": round(
                        change_percent,
                        1,
                    ),
                    "sessions_7_days": (
                        sessions_7
                    ),
                },
                confidence=0.9,
                magnitude=clamp(
                    abs(change_percent) / 60,
                    0.8,
                    1.5,
                ),
                recency=1.1,
            )
        )

    return findings


def get_finding_group(
    finding: dict[str, Any],
) -> str:
    """
    Ordnet inhaltlich ähnliche Findings einer gemeinsamen
    Gruppe zu.

    Dadurch werden unterschiedliche Codes, die denselben
    Trainingssachverhalt beschreiben, nicht mehrfach
    ausgegeben.
    """

    code = normalize_dimension_name(
        finding.get(
            "code",
            "unknown",
        )
    )

    groups = {
        "missing_horizontal_pull": (
            "horizontal_push_pull_balance"
        ),
        "horizontal_pull_not_recent": (
            "horizontal_push_pull_balance"
        ),
        "imbalance_horizontal_push_to_horizontal_pull": (
            "horizontal_push_pull_balance"
        ),
        "missing_vertical_pull": (
            "vertical_push_pull_balance"
        ),
        "vertical_pull_not_recent": (
            "vertical_push_pull_balance"
        ),
        "imbalance_vertical_push_to_vertical_pull": (
            "vertical_push_pull_balance"
        ),
        "missing_hinge": (
            "squat_hinge_balance"
        ),
        "hinge_not_recent": (
            "squat_hinge_balance"
        ),
        "imbalance_squat_to_hinge": (
            "squat_hinge_balance"
        ),
        "rapid_weekly_load_increase": (
            "weekly_load_increase"
        ),
        "weekly_load_progression_high": (
            "weekly_load_increase"
        ),
        "repeated_high_rpe": (
            "high_intensity_density"
        ),
        "repeated_very_high_rpe": (
            "very_high_intensity_density"
        ),
        "limited_recovery_distribution": (
            "high_intensity_density"
        ),
        "insufficient_easy_sessions": (
            "missing_easy_session"
        ),
        "high_density_without_easy_session": (
            "missing_easy_session"
        ),
    }

    return groups.get(
        code,
        code,
    )


def deduplicate_findings(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Entfernt exakte und inhaltlich ähnliche Findings.

    Innerhalb einer Finding-Gruppe bleibt das Finding mit
    dem höchsten Impact-Score erhalten.
    """

    findings_by_group: dict[
        str,
        dict[str, Any],
    ] = {}

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        group = get_finding_group(
            finding
        )

        existing = findings_by_group.get(
            group
        )

        if existing is None:
            findings_by_group[group] = (
                finding
            )
            continue

        existing_score = safely_get_int(
            existing.get("impact_score")
        )

        new_score = safely_get_int(
            finding.get("impact_score")
        )

        if new_score > existing_score:
            findings_by_group[group] = (
                finding
            )

    return list(
        findings_by_group.values()
    )


def normalize_primary_goal(
    primary_goal: str | None,
) -> str | None:
    """Normalisiert das Athletenziel für die Priorisierung."""

    if primary_goal is None:
        return None

    normalized = normalize_dimension_name(
        primary_goal
    )

    return GOAL_ALIASES.get(
        normalized,
        GOAL_ALIASES.get(
            str(primary_goal).strip().casefold()
        ),
    )


def prioritize_findings_for_goal(
    findings: list[dict[str, Any]],
    *,
    primary_goal: str | None,
) -> list[dict[str, Any]]:
    """
    Gewichtet Findings für das persönliche Ziel.

    Der ursprüngliche impact_score bleibt als
    base_impact_score erhalten. Überlastungs- und
    Regenerationswarnungen werden niemals ausgeblendet.
    """

    goal = normalize_primary_goal(
        primary_goal
    )

    if goal is None:
        return [dict(finding) for finding in findings]

    category_weights = GOAL_CATEGORY_WEIGHTS.get(
        goal,
        {},
    )
    code_weights = GOAL_CODE_WEIGHTS.get(
        goal,
        {},
    )
    ignored_codes = GOAL_IGNORED_CODES.get(
        goal,
        set(),
    )

    prioritized: list[dict[str, Any]] = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        item = dict(finding)
        code = normalize_dimension_name(
            item.get("code", "unknown")
        )
        category = normalize_dimension_name(
            item.get("category", "unknown")
        )
        finding_type = normalize_dimension_name(
            item.get("type", "unknown")
        )

        safety_relevant = finding_type in {
            "overload",
            "recovery",
            "progression",
        }

        if code in ignored_codes and not safety_relevant:
            continue

        base_score = safely_get_int(
            item.get("impact_score")
        )
        category_weight = category_weights.get(
            category,
            1.0,
        )
        code_weight = code_weights.get(
            code,
            1.0,
        )
        goal_weight = category_weight * code_weight

        # Sicherheitsrelevante Findings dürfen durch das Ziel
        # nicht heruntergestuft werden.
        if safety_relevant:
            goal_weight = max(
                goal_weight,
                1.0,
            )

        goal_score = int(
            round(
                clamp(
                    base_score * goal_weight,
                    0,
                    100,
                )
            )
        )

        item["base_impact_score"] = base_score
        item["goal_weight"] = round(
            goal_weight,
            2,
        )
        item["goal_impact_score"] = goal_score
        item["impact_score"] = goal_score
        item["primary_goal"] = goal
        prioritized.append(item)

    return prioritized


def sort_findings(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sortiert Findings nach Relevanz.
    """

    severity_order = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    return sorted(
        findings,
        key=lambda finding: (
            safely_get_int(
                finding.get(
                    "impact_score"
                )
            ),
            severity_order.get(
                str(
                    finding.get(
                        "severity",
                        "low",
                    )
                ),
                0,
            ),
        ),
        reverse=True,
    )


def build_analysis_overview(
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Erstellt eine kompakte Zusammenfassung für Dashboard,
    Coach und spätere Reports.
    """

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for finding in findings:
        finding_type = str(
            finding.get(
                "type",
                "unknown",
            )
        )

        severity = str(
            finding.get(
                "severity",
                "unknown",
            )
        )

        by_type[finding_type] = (
            by_type.get(
                finding_type,
                0,
            )
            + 1
        )

        by_severity[severity] = (
            by_severity.get(
                severity,
                0,
            )
            + 1
        )

    highest_impact = (
        safely_get_int(
            findings[0].get(
                "impact_score"
            )
        )
        if findings
        else 0
    )

    if highest_impact >= 80:
        status = "red"
    elif highest_impact >= 50:
        status = "yellow"
    else:
        status = "green"

    return {
        "status": status,
        "finding_count": len(findings),
        "highest_impact_score": (
            highest_impact
        ),
        "by_type": by_type,
        "by_severity": by_severity,
        "top_codes": [
            str(finding.get("code"))
            for finding in findings[:5]
        ],
    }


def build_findings(
    history_summary: dict[str, Any],
    *,
    primary_goal: str | None = None,
    maximum_findings: int | None = None,
) -> dict[str, Any]:
    """
    Führt alle regelbasierten Analysen aus.

    Rückgabeformat:

    {
        "overview": {...},
        "findings": [...],
        "top_findings": [...],
    }

    Die Funktion verändert history_summary nicht.
    """

    if not isinstance(
        history_summary,
        dict,
    ):
        history_summary = {}

    all_findings: list[
        dict[str, Any]
    ] = []

    all_findings.extend(
        analyze_overload(
            history_summary
        )
    )

    all_findings.extend(
        analyze_undertraining(
            history_summary
        )
    )

    all_findings.extend(
        analyze_balance(
            history_summary
        )
    )

    all_findings.extend(
        analyze_recovery(
            history_summary
        )
    )

    all_findings.extend(
        analyze_progression(
            history_summary
        )
    )

    unique_findings = (
        deduplicate_findings(
            all_findings
        )
    )

    goal_prioritized_findings = (
        prioritize_findings_for_goal(
            unique_findings,
            primary_goal=primary_goal,
        )
    )

    sorted_results = sort_findings(
        goal_prioritized_findings
    )

    if (
        maximum_findings is not None
        and maximum_findings >= 0
    ):
        returned_findings = (
            sorted_results[
                :maximum_findings
            ]
        )
    else:
        returned_findings = (
            sorted_results
        )

    overview = build_analysis_overview(
        sorted_results
    )

    return {
        "overview": {
            **overview,
            "primary_goal": (
                normalize_primary_goal(
                    primary_goal
                )
            ),
        },
        "findings": returned_findings,
        "top_findings": (
            sorted_results[:5]
        ),
    }