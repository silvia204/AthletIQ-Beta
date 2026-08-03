from __future__ import annotations

from typing import Any, Mapping


GOAL_ALIASES = {
    "crossfit": "crossfit",
    "cross fit": "crossfit",
    "hyrox": "hyrox",
    "general fitness": "general_fitness",
    "general_fitness": "general_fitness",
    "fitness": "general_fitness",
    "abnehmen": "weight_loss",
    "weight loss": "weight_loss",
    "weight_loss": "weight_loss",

    # Fünftes Bewegungsziel: Laufen
    "laufen": "running",
    "lauf": "running",
    "running": "running",
    "run": "running",
    "halbmarathon": "running",
    "halb marathon": "running",
    "half marathon": "running",
    "half_marathon": "running",
    "marathon": "running",
    "marathon laufen": "running",
    "marathon_running": "running",
}

DIMENSION_LABELS = {
    "muscle_groups": {
        "quads": "Quadrizeps",
        "hamstrings": "Hamstrings",
        "glutes": "Gesäß",
        "calves": "Waden",
        "back": "Rücken",
        "lats": "Latissimus",
        "chest": "Brust",
        "shoulders": "Schultern",
        "biceps": "Bizeps",
        "triceps": "Trizeps",
        "core": "Core",
        "legs": "Beine",
        "upper_body": "Oberkörper",
        "full_body": "Ganzkörper",
        "tibialis_anterior": "Vorderer Schienbeinmuskel",
        "hip_flexors": "Hüftbeuger",
        "hip_abductors": "Hüftabduktoren",
        "adductors": "Adduktoren",
        "spinal_erectors": "Rückenstrecker",
        "feet_ankles": "Fuß- und Sprunggelenksmuskulatur",
    },
    "movement_patterns": {
        "squat": "Squat",
        "hinge": "Hinge",
        "lunge": "Lunge",
        "horizontal_push": "Horizontales Drücken",
        "vertical_push": "Vertikales Drücken",
        "horizontal_pull": "Horizontales Ziehen",
        "vertical_pull": "Vertikales Ziehen",
        "carry": "Carries",
        "core": "Core",
        "locomotion": "Laufen / Locomotion",
        "rotation": "Rotation",
        "single_leg": "Einbeinige Stabilität",
        "ankle_extension": "Sprunggelenksstreckung",
        "mobility": "Mobilität",
    },
    "training_goals": {
        "max_strength": "Maximalkraft",
        "hypertrophy": "Muskelaufbau",
        "strength_endurance": "Kraftausdauer",
        "speed_strength": "Schnellkraft",
        "explosive_strength": "Explosivkraft",
        "aerobic_base": "Aerobe Basis",
        "threshold": "Schwelle",
        "vo2max": "VO₂max",
        "anaerobic_capacity": "Anaerobe Kapazität",
        "technique": "Technik",
        "mobility": "Mobilität",
        "recovery": "Regeneration",
        "easy_run": "Lockerer Lauf",
        "long_run": "Langer Lauf",
        "tempo_run": "Tempolauf",
        "race_pace": "Wettkampftempo",
        "running_economy": "Laufökonomie",
        "hill_running": "Berglauf",
        "race_specific": "Wettkampfspezifisch",
        "aerobic_power": "Aerobe Leistungsfähigkeit",
        "lactate_threshold": "Laktatschwelle",
        "active_recovery": "Aktive Regeneration",
        "stability": "Stabilität",
    },
    "load_types": {
        "low_intensity": "Niedrige Intensität",
        "moderate_intensity": "Mittlere Intensität",
        "high_intensity": "Hohe Intensität",
        "strength": "Kraftbelastung",
        "cardio": "Ausdauerbelastung",
        "mixed": "Gemischte Belastung",
        "impact": "Stoßbelastung",
        "eccentric": "Exzentrische Belastung",
        "isometric": "Isometrische Belastung",
        "metabolic": "Metabolische Belastung",
        "mechanical": "Mechanische Belastung",
        "neuromuscular": "Neuromuskuläre Belastung",
        "cyclic": "Zyklische Belastung",
    },
}

# Zielbereiche sind Anteile am jeweiligen 28-Tage-Dimensionsvolumen.
# Fehlende Kategorien werden über DEFAULT_TARGETS neutral eingeordnet.
DEFAULT_TARGETS = {
    "muscle_groups": (0.04, 0.22),
    "movement_patterns": (0.04, 0.20),
    "training_goals": (0.03, 0.22),
    "load_types": (0.05, 0.40),
}

TARGET_RANGES: dict[str, dict[str, dict[str, tuple[float, float]]]] = {
    "hyrox": {
        "movement_patterns": {
            "locomotion": (0.22, 0.42),
            "squat": (0.07, 0.18),
            "hinge": (0.06, 0.16),
            "lunge": (0.06, 0.16),
            "carry": (0.05, 0.15),
            "horizontal_push": (0.03, 0.10),
            "horizontal_pull": (0.03, 0.10),
            "vertical_push": (0.02, 0.08),
            "vertical_pull": (0.02, 0.08),
            "core": (0.04, 0.12),
            "rotation": (0.01, 0.06),
        },
        "training_goals": {
            "aerobic_base": (0.18, 0.35),
            "threshold": (0.08, 0.20),
            "vo2max": (0.04, 0.14),
            "strength_endurance": (0.12, 0.28),
            "max_strength": (0.05, 0.15),
            "technique": (0.03, 0.10),
            "mobility": (0.03, 0.10),
            "recovery": (0.03, 0.10),
        },
    },
    "crossfit": {
        "movement_patterns": {
            "squat": (0.08, 0.18),
            "hinge": (0.08, 0.18),
            "horizontal_push": (0.04, 0.12),
            "vertical_push": (0.05, 0.14),
            "horizontal_pull": (0.04, 0.12),
            "vertical_pull": (0.05, 0.14),
            "carry": (0.03, 0.10),
            "core": (0.05, 0.13),
            "locomotion": (0.08, 0.22),
            "rotation": (0.02, 0.08),
            "lunge": (0.04, 0.12),
        },
        "training_goals": {
            "max_strength": (0.10, 0.24),
            "strength_endurance": (0.10, 0.24),
            "speed_strength": (0.04, 0.14),
            "explosive_strength": (0.04, 0.14),
            "aerobic_base": (0.08, 0.20),
            "threshold": (0.05, 0.15),
            "vo2max": (0.04, 0.14),
            "technique": (0.05, 0.15),
            "mobility": (0.03, 0.10),
            "recovery": (0.03, 0.10),
        },
    },
    "general_fitness": {
        "movement_patterns": {
            "squat": (0.06, 0.15),
            "hinge": (0.06, 0.15),
            "lunge": (0.04, 0.12),
            "horizontal_push": (0.04, 0.12),
            "vertical_push": (0.03, 0.10),
            "horizontal_pull": (0.04, 0.12),
            "vertical_pull": (0.03, 0.10),
            "carry": (0.03, 0.10),
            "core": (0.05, 0.14),
            "locomotion": (0.12, 0.28),
            "rotation": (0.03, 0.10),
        },
        "training_goals": {
            "max_strength": (0.06, 0.18),
            "hypertrophy": (0.06, 0.18),
            "strength_endurance": (0.06, 0.18),
            "aerobic_base": (0.16, 0.32),
            "threshold": (0.04, 0.14),
            "technique": (0.04, 0.12),
            "mobility": (0.05, 0.14),
            "recovery": (0.04, 0.12),
        },
    },

    "running": {
        # Marathon- und Halbmarathontraining wird primär über die
        # Laufbewegung getragen. Ergänzende Kraft-, Stabilitäts- und
        # Mobilitätsmuster bleiben bewusst im Zielkorridor.
        "movement_patterns": {
            "locomotion": (0.48, 0.72),
            "single_leg": (0.06, 0.16),
            "hinge": (0.04, 0.12),
            "squat": (0.03, 0.10),
            "lunge": (0.03, 0.10),
            "core": (0.04, 0.12),
            "rotation": (0.01, 0.06),
            "carry": (0.01, 0.06),
            "horizontal_push": (0.01, 0.06),
            "horizontal_pull": (0.01, 0.06),
            "vertical_push": (0.00, 0.04),
            "vertical_pull": (0.00, 0.04),
            "ankle_extension": (0.02, 0.10),
            "mobility": (0.02, 0.10),
        },
        "training_goals": {
            "aerobic_base": (0.28, 0.46),
            "easy_run": (0.18, 0.38),
            "long_run": (0.12, 0.26),
            "threshold": (0.06, 0.16),
            "lactate_threshold": (0.06, 0.16),
            "tempo_run": (0.05, 0.15),
            "vo2max": (0.03, 0.11),
            "race_pace": (0.03, 0.12),
            "race_specific": (0.03, 0.12),
            "running_economy": (0.02, 0.10),
            "hill_running": (0.01, 0.08),
            "max_strength": (0.03, 0.10),
            "strength_endurance": (0.03, 0.10),
            "stability": (0.02, 0.09),
            "mobility": (0.02, 0.09),
            "recovery": (0.03, 0.12),
            "active_recovery": (0.03, 0.12),
        },
        "muscle_groups": {
            "quads": (0.12, 0.24),
            "hamstrings": (0.10, 0.22),
            "glutes": (0.10, 0.22),
            "calves": (0.08, 0.18),
            "core": (0.06, 0.16),
            "tibialis_anterior": (0.02, 0.09),
            "hip_flexors": (0.03, 0.10),
            "hip_abductors": (0.03, 0.10),
            "adductors": (0.02, 0.08),
            "spinal_erectors": (0.02, 0.08),
            "feet_ankles": (0.02, 0.09),
            "back": (0.01, 0.06),
            "chest": (0.00, 0.04),
            "shoulders": (0.00, 0.04),
            "biceps": (0.00, 0.03),
            "triceps": (0.00, 0.03),
        },
        "load_types": {
            "cardio": (0.34, 0.58),
            "metabolic": (0.28, 0.52),
            "cyclic": (0.20, 0.48),
            "impact": (0.12, 0.28),
            "low_intensity": (0.25, 0.48),
            "moderate_intensity": (0.10, 0.26),
            "high_intensity": (0.05, 0.16),
            "mechanical": (0.05, 0.16),
            "neuromuscular": (0.02, 0.10),
            "eccentric": (0.02, 0.10),
            "strength": (0.03, 0.12),
            "mixed": (0.02, 0.10),
            "isometric": (0.00, 0.05),
        },
    },
    "weight_loss": {
        "movement_patterns": {
            "locomotion": (0.18, 0.38),
            "squat": (0.06, 0.16),
            "hinge": (0.06, 0.16),
            "lunge": (0.04, 0.12),
            "horizontal_push": (0.03, 0.10),
            "vertical_push": (0.02, 0.08),
            "horizontal_pull": (0.03, 0.10),
            "vertical_pull": (0.02, 0.08),
            "carry": (0.03, 0.10),
            "core": (0.04, 0.12),
            "rotation": (0.02, 0.08),
        },
        "training_goals": {
            "aerobic_base": (0.22, 0.42),
            "strength_endurance": (0.10, 0.24),
            "max_strength": (0.05, 0.15),
            "hypertrophy": (0.05, 0.15),
            "threshold": (0.04, 0.14),
            "mobility": (0.04, 0.12),
            "recovery": (0.04, 0.12),
        },
    },
}

STATUS_META = {
    "underrepresented": {"label": "Unterrepräsentiert", "symbol": "↓", "priority": 3},
    "balanced": {"label": "Ausgewogen", "symbol": "✓", "priority": 0},
    "overrepresented": {"label": "Überrepräsentiert", "symbol": "↑", "priority": 3},
    "no_data": {"label": "Keine Daten", "symbol": "•", "priority": 1},
}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalize_goal(primary_goal: str | None) -> str:
    raw = str(primary_goal or "general_fitness").strip().casefold()
    return GOAL_ALIASES.get(raw, raw.replace(" ", "_"))


def _label(dimension: str, key: str) -> str:
    return DIMENSION_LABELS.get(dimension, {}).get(
        key,
        str(key).replace("_", " ").title(),
    )


def _target_range(goal: str, dimension: str, key: str) -> tuple[float, float]:
    return TARGET_RANGES.get(goal, {}).get(dimension, {}).get(
        key,
        DEFAULT_TARGETS[dimension],
    )


def _status(share: float, low: float, high: float, total: float) -> str:
    if total <= 0:
        return "no_data"
    if share < low:
        return "underrepresented"
    if share > high:
        return "overrepresented"
    return "balanced"


def _trend(current: float, previous: float) -> dict[str, Any]:
    if previous <= 0 and current <= 0:
        return {"direction": "stable", "symbol": "→", "change_percent": None}
    if previous <= 0:
        return {"direction": "up", "symbol": "↗", "change_percent": None}

    change = ((current - previous) / previous) * 100
    if change > 20:
        direction, symbol = "up", "↗"
    elif change < -20:
        direction, symbol = "down", "↘"
    else:
        direction, symbol = "stable", "→"

    return {
        "direction": direction,
        "symbol": symbol,
        "change_percent": round(change, 1),
    }


def _previous_14_counts(window_28: Mapping[str, Any], window_14: Mapping[str, Any], dimension: str) -> dict[str, float]:
    all_28 = window_28.get(dimension, {}) or {}
    current_14 = window_14.get(dimension, {}) or {}
    keys = set(all_28) | set(current_14)
    return {
        key: max(0.0, _safe_float(all_28.get(key)) - _safe_float(current_14.get(key)))
        for key in keys
    }


def evaluate_dimension(
    *,
    dimension: str,
    counts_28: Mapping[str, Any],
    counts_14: Mapping[str, Any],
    previous_14: Mapping[str, Any],
    goal: str,
) -> list[dict[str, Any]]:
    keys = set(counts_28) | set(counts_14) | set(previous_14)
    keys |= set(TARGET_RANGES.get(goal, {}).get(dimension, {}))

    total_28 = sum(max(0.0, _safe_float(value)) for value in counts_28.values())
    rows: list[dict[str, Any]] = []

    for key in sorted(keys):
        value_28 = max(0.0, _safe_float(counts_28.get(key)))
        share = value_28 / total_28 if total_28 > 0 else 0.0
        low, high = _target_range(goal, dimension, key)
        status = _status(share, low, high, total_28)
        trend = _trend(
            max(0.0, _safe_float(counts_14.get(key))),
            max(0.0, _safe_float(previous_14.get(key))),
        )

        distance = 0.0
        if status == "underrepresented" and low > 0:
            distance = (low - share) / low
        elif status == "overrepresented" and high > 0:
            distance = (share - high) / high

        trend_risk = 0.0
        if status == "underrepresented" and trend["direction"] == "down":
            trend_risk = 0.35
        elif status == "overrepresented" and trend["direction"] == "up":
            trend_risk = 0.35

        priority_score = round(
            STATUS_META[status]["priority"] + min(distance, 2.0) + trend_risk,
            3,
        )

        rows.append({
            "key": key,
            "label": _label(dimension, key),
            "value_28": round(value_28, 2),
            "share": round(share, 4),
            "share_percent": round(share * 100, 1),
            "target_min_percent": round(low * 100, 1),
            "target_max_percent": round(high * 100, 1),
            "status": status,
            "status_label": STATUS_META[status]["label"],
            "status_symbol": STATUS_META[status]["symbol"],
            "trend_direction": trend["direction"],
            "trend_symbol": trend["symbol"],
            "trend_change_percent": trend["change_percent"],
            "priority_score": priority_score,
        })

    return sorted(
        rows,
        key=lambda item: (-item["priority_score"], -item["share"], item["label"]),
    )


def build_balance_findings(balance: Mapping[str, Any], max_items: int = 6) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for dimension in ("movement_patterns", "training_goals", "muscle_groups", "load_types"):
        for item in balance.get(dimension, []):
            if item["status"] not in {"underrepresented", "overrepresented"}:
                continue

            direction_text = "nimmt zusätzlich ab" if item["trend_direction"] == "down" else (
                "nimmt zusätzlich zu" if item["trend_direction"] == "up" else "ist zuletzt stabil"
            )
            findings.append({
                "dimension": dimension,
                "key": item["key"],
                "title": f"{item['label']}: {item['status_label']}",
                "text": (
                    f"{item['share_percent']:.1f} % Anteil in 28 Tagen; "
                    f"Zielbereich {item['target_min_percent']:.1f}–"
                    f"{item['target_max_percent']:.1f} %. Der 14-Tage-Trend {direction_text}."
                ),
                "status": item["status"],
                "priority_score": item["priority_score"],
            })

    return sorted(findings, key=lambda item: -item["priority_score"])[:max_items]


def build_training_balance(
    trend_analysis: Mapping[str, Any],
    *,
    primary_goal: str | None = None,
) -> dict[str, Any]:
    goal = _normalize_goal(primary_goal)
    windows = trend_analysis.get("windows", {}) or {}
    window_14 = windows.get("14_days", {}) or {}
    window_28 = windows.get("28_days", {}) or {}

    result: dict[str, Any] = {
        "primary_goal": goal,
        "period_days": 28,
        "trend_days": 14,
    }

    for dimension in ("muscle_groups", "movement_patterns", "training_goals", "load_types"):
        counts_28 = window_28.get(dimension, {}) or {}
        counts_14 = window_14.get(dimension, {}) or {}
        previous_14 = _previous_14_counts(window_28, window_14, dimension)
        result[dimension] = evaluate_dimension(
            dimension=dimension,
            counts_28=counts_28,
            counts_14=counts_14,
            previous_14=previous_14,
            goal=goal,
        )

    result["findings"] = build_balance_findings(result)
    result["overview"] = {
        "underrepresented": sum(
            item["status"] == "underrepresented"
            for dimension in ("muscle_groups", "movement_patterns", "training_goals", "load_types")
            for item in result[dimension]
        ),
        "overrepresented": sum(
            item["status"] == "overrepresented"
            for dimension in ("muscle_groups", "movement_patterns", "training_goals", "load_types")
            for item in result[dimension]
        ),
    }
    return result