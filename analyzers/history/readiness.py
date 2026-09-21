"""Readiness-Bewertung anhand der Trainingshistorie."""
from __future__ import annotations

LOCAL_LOAD_NOTICE_CODES = {
    "high_mechanical_load",
    "high_eccentric_load",
    "high_impact_load",
    "high_neuromuscular_load",
}
MUSCLE_LOAD_NOTICE_PREFIX = "high_recent_"


def _has_relevant_local_accumulation(overload_signals: list[dict]) -> bool:
    """Mindestens 1 erhöhte Belastungsart + 3 stark belastete Muskelgruppen."""
    notice_codes = {
        str(signal.get("code", "")).strip()
        for signal in overload_signals
        if signal.get("severity") == "notice"
    }
    load_type_count = sum(code in LOCAL_LOAD_NOTICE_CODES for code in notice_codes)
    muscle_count = sum(
        code.startswith(MUSCLE_LOAD_NOTICE_PREFIX)
        for code in notice_codes
    )
    return load_type_count >= 1 and muscle_count >= 3


def analyze_readiness(history_summary: dict) -> dict:
    """
    Priorität:
    - >= 2 Warnings -> low
    - 1 Warning -> moderate
    - 0 Warnings + relevante lokale Akkumulation -> moderate
    - sonst -> high
    """
    overload = history_summary.get("overload_signals", [])
    undertraining = history_summary.get("undertraining_signals", [])

    warning_count = sum(
        1 for signal in overload
        if signal.get("severity") == "warning"
    )
    notice_count = len(overload) + len(undertraining) - warning_count
    local_accumulation = _has_relevant_local_accumulation(overload)

    if warning_count >= 2:
        status = "low"
        status_reason = "multiple_warnings"
    elif warning_count == 1:
        status = "moderate"
        status_reason = "warning"
    elif local_accumulation:
        status = "moderate"
        status_reason = "local_load_accumulation"
    else:
        status = "high"
        status_reason = "no_relevant_warning"

    return {
        "status": status,
        "status_reason": status_reason,
        "warning_count": warning_count,
        "notice_count": notice_count,
        "local_load_accumulation": local_accumulation,
        "overload_signals": overload,
        "undertraining_signals": undertraining,
    }
