"""
coach_context.py

Kontrollierte Datengrundlage für den History-Coach.

Der LLM-Coach erhält nur bereits deterministisch berechnete bzw.
rein beschreibend verdichtete Fakten. Rohdaten der vollständigen
Historie werden nicht an Mistral weitergereicht.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from models.training_analysis import TrainingAnalysis

from services.training_balance import assess_muscle_group_balance


def _messages(
    items: list[dict] | None,
    *,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> list[str]:
    result: list[str] = []

    for item in items or []:
        if not isinstance(item, dict):
            continue

        code = str(item.get("code", "") or "").strip()

        if allowed_prefixes is not None:
            if not any(
                code.startswith(prefix)
                for prefix in allowed_prefixes
            ):
                continue

        message = str(item.get("message", "") or "").strip()
        if message:
            result.append(message)

    return result


def _positive_facts(
    observations: list[dict] | None,
) -> list[str]:
    """
    Readiness- und pauschale Konsistenz-Lobs werden bewusst
    nicht an den History-Coach weitergegeben.
    """
    result: list[str] = []

    excluded_codes = {
        "good_readiness",
        "good_consistency",
    }

    for item in observations or []:
        if not isinstance(item, dict):
            continue

        code = str(item.get("code", "") or "").strip()
        if code in excluded_codes:
            continue

        message = str(item.get("message", "") or "").strip()
        if message:
            result.append(message)

    return result


def _top_distribution(
    values: dict | None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """
    Verdichtet eine bereits aggregierte Trainingsdimension rein
    beschreibend. Es werden keine fachlichen Schlüsse gezogen.
    """
    cleaned: list[tuple[str, float]] = []

    for key, value in (values or {}).items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue

        if numeric > 0:
            cleaned.append((str(key), numeric))

    cleaned.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    total = sum(value for _, value in cleaned)

    result: list[dict[str, Any]] = []
    for key, value in cleaned[:limit]:
        result.append(
            {
                "name": key,
                "relative_share_percent": (
                    round(value / total * 100.0, 1)
                    if total > 0
                    else 0.0
                ),
            }
        )

    return result


def _distribution(values: dict | None) -> dict[str, float]:
    """Bereinigt eine bereits deterministisch aggregierte Dimension."""
    result: dict[str, float] = {}
    for key, value in (values or {}).items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric > 0:
            result[str(key)] = round(numeric, 3)
    return result


def _undertraining_by_dimension(signals: list[dict] | None) -> dict[str, list[str]]:
    """Ordnet deterministische Undertraining-Signale ihren Analysebereichen zu."""
    result = {"movement_patterns": [], "muscle_groups": [], "training_goals": []}
    muscle_codes = (
        "quadriceps_to_hamstrings", "chest_to_latissimus", "front_to_rear_delts",
        "hamstrings_not_recent", "glutes_not_recent", "latissimus_not_recent",
        "rear_delts_not_recent", "deep_core_not_recent",
    )
    for item in signals or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "") or "")
        message = str(item.get("message", "") or "").strip()
        if not message:
            continue
        if code.startswith(("missing_goal_", "goal_")):
            result["training_goals"].append(message)
        elif code in muscle_codes:
            result["muscle_groups"].append(message)
        elif code.startswith(("missing_", "squat_", "hinge_", "horizontal_", "vertical_", "carry_", "anti_")):
            result["movement_patterns"].append(message)
    return result


def _training_recency(
    history_summary: dict,
    sportart: str,
) -> dict[str, Any]:
    windows = history_summary.get("windows", {})

    sessions_7 = int(
        windows.get("7_days", {}).get("sessions", 0) or 0
    )
    sessions_14 = int(
        windows.get("14_days", {}).get("sessions", 0) or 0
    )

    previous_7_sessions = max(
        0,
        sessions_14 - sessions_7,
    )

    recent_sessions = history_summary.get(
        "letzte_einheiten",
        [],
    )

    last_workout_date: str | None = None
    days_since_last_workout: int | None = None

    if recent_sessions:
        raw_date = str(
            recent_sessions[-1].get("zeitstempel", "") or ""
        ).strip()

        if raw_date and raw_date != "Unbekannt":
            try:
                parsed = date.fromisoformat(raw_date)
                last_workout_date = parsed.isoformat()
                days_since_last_workout = max(
                    0,
                    (date.today() - parsed).days,
                )
            except ValueError:
                pass

    if sessions_7 == 0:
        rhythm_note = (
            "In den letzten 7 Tagen wurde keine "
            "Trainingseinheit dokumentiert."
        )
    elif previous_7_sessions == 0:
        rhythm_note = (
            "In den letzten 7 Tagen wurden "
            f"{sessions_7} Einheiten dokumentiert; "
            "in den 7 Tagen davor keine."
        )
    elif sessions_7 != previous_7_sessions:
        rhythm_note = (
            f"In den letzten 7 Tagen wurden {sessions_7} "
            "Einheiten dokumentiert, in den 7 Tagen davor "
            f"{previous_7_sessions}."
        )
    else:
        rhythm_note = (
            f"In den letzten beiden 7-Tage-Zeiträumen wurden "
            f"jeweils {sessions_7} Einheiten dokumentiert."
        )

    return {
        "sessions_last_7_days": sessions_7,
        "sessions_previous_7_days": previous_7_sessions,
        "last_workout_date": last_workout_date,
        "days_since_last_workout": days_since_last_workout,
        "rhythm_note": rhythm_note,
    }


def build_history_coach_context(
    *,
    training_analysis: TrainingAnalysis,
    readiness: dict,
    weekly_focus: dict,
    positive_observations: list[dict],
    history_summary: dict,
    sportart: str,
) -> dict[str, Any]:
    """
    Erstellt zwei getrennte Faktenblöcke:

    readiness_summary_facts:
        ausschließlich für den Kurztext in der Ampelkarte.

    history_coach_facts:
        ausschließlich für die längerfristige Coach-Einordnung.

    Muskelgruppen-Undertraining und Readiness werden dem eigentlichen
    History-Coach bewusst nicht als Interpretationsgrundlage gegeben.
    """

    overview = training_analysis.overview or {}
    trends = training_analysis.trends or {}
    movement_coverage = training_analysis.movement_coverage or {}

    windows = trends.get("windows", {})
    window_28 = windows.get("28_days", {})

    recency = _training_recency(
        history_summary,
        sportart,
    )

    allowed_undertraining = _messages(
        readiness.get("undertraining_signals", []),
        allowed_prefixes=(
            "missing_squat",
            "missing_hinge",
            "missing_horizontal_push",
            "missing_vertical_push",
            "missing_horizontal_pull",
            "missing_vertical_pull",
            "missing_carry",
            "missing_anti_rotation",
            "missing_anti_extension",
            "squat_not_recent",
            "hinge_not_recent",
            "horizontal_push_not_recent",
            "vertical_push_not_recent",
            "horizontal_pull_not_recent",
            "vertical_pull_not_recent",
            "carry_not_recent",
            "anti_rotation_not_recent",
            "anti_extension_not_recent",
            "missing_goal_",
            "goal_",
        ),
    )

    weekly_focus_context: dict[str, Any] = {}

    focus_reason = str(
        weekly_focus.get("reason", "") or ""
    ).strip()

    # Readiness-basierte kurzfristige Focus-Texte werden nicht in
    # die längerfristige Coach-Einordnung übernommen.
    if (
        weekly_focus.get("reason") != "readiness_low"
        and focus_reason
        and focus_reason in allowed_undertraining
    ):
        weekly_focus_context = {
            "focus": focus_reason,
            "priority": str(
                weekly_focus.get("priority", "") or ""
            ).strip(),
        }

    return {
        "readiness_summary_facts": {
            "status": str(
                readiness.get("status", "high") or "high"
            ),
            "overload_signals": _messages(
                readiness.get("overload_signals", [])
            ),
        },
        "history_coach_facts": {
            "training_recency": recency,
            "history_overview_28_days": {
                "sessions": int(
                    overview.get("sessions", 0) or 0
                ),
                "minutes": int(
                    overview.get("minutes", 0) or 0
                ),
                "average_rpe": overview.get(
                    "average_rpe"
                ),
            },
            "readiness": {
                "status": str(readiness.get("status", "high") or "high"),
                "overload_signals": _messages(readiness.get("overload_signals", [])),
            },
            "training_dimensions_28_days": {
                "movement_patterns": _distribution(window_28.get("movement_pattern_load")),
                "muscle_groups": _distribution(window_28.get("muscle_group_load")),
                "training_goals": _distribution(window_28.get("training_goal_counts")),
                "load_types": _distribution(window_28.get("load_type_load")),
            },
            "underrepresented_by_dimension": _undertraining_by_dimension(
                readiness.get("undertraining_signals", [])
            ),
            "muscle_group_target_assessment": assess_muscle_group_balance(
                _distribution(window_28.get("muscle_group_load")),
                sportart,
            ),
            "movement_coverage": {
                "coverage_percent": float(
                    movement_coverage.get(
                        "coverage_percent",
                        0.0,
                    )
                    or 0.0
                ),
                "covered": int(
                    movement_coverage.get("covered", 0) or 0
                ),
                "expected": int(
                    movement_coverage.get("expected", 0) or 0
                ),
            },
            "crossfit": {
                "coverage": history_summary.get("crossfit_coverage", {}),
                "missing_movements": history_summary.get("missing_crossfit_movements", []),
                "completed_movements": history_summary.get("crossfit_movements", {}),
            },
            "underrepresented_areas": allowed_undertraining,
            "positive_observations": _positive_facts(
                positive_observations
            ),
            "weekly_focus": weekly_focus_context,
        },
    }
