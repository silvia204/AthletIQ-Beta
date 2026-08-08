"""
readiness.py

Bewertet die aktuelle Trainingsbereitschaft anhand
der Trainingshistorie.
"""

from __future__ import annotations


def analyze_readiness(
    history_summary: dict,
) -> dict:
    """
    Leitet eine einfache Readiness-Bewertung aus
    Überlastungs- und Untertrainingssignalen ab.
    """

    overload = history_summary.get(
        "overload_signals",
        [],
    )

    undertraining = history_summary.get(
        "undertraining_signals",
        [],
    )

    warning_count = sum(
        1
        for signal in overload
        if signal.get("severity") == "warning"
    )

    notice_count = (
        len(overload)
        + len(undertraining)
        - warning_count
    )

    if warning_count >= 2:
        status = "low"

    elif warning_count == 1:
        status = "moderate"

    else:
        status = "high"

    return {
        "status": status,
        "warning_count": warning_count,
        "notice_count": notice_count,
        "overload_signals": overload,
        "undertraining_signals": undertraining,
    }