"""
weekly_focus.py

Leitet einen Schwerpunkt für die kommende Trainingswoche ab.
"""

from __future__ import annotations


def analyze_weekly_focus(
    *,
    history_summary: dict,
    readiness: dict,
) -> dict:
    """
    Ermittelt den empfohlenen Schwerpunkt der nächsten Woche.
    """

    overload = history_summary.get(
        "overload_signals",
        []
    )

    undertraining = history_summary.get(
        "undertraining_signals",
        []
    )

    readiness_status = readiness.get(
        "status",
        "high",
    )

    if readiness_status == "low":
        return {
            "title": "Belastung vorübergehend reduzieren",
            "text": (
                "Wenn innerhalb der nächsten 24–48 Stunden Training geplant ist, "
                "reduziere Intensität oder Umfang deutlich oder ersetze die Einheit "
                "durch aktive Regeneration. Liegt dein nächstes Training später, "
                "beurteile deine Belastbarkeit zu diesem Zeitpunkt erneut."
            ),
            "reason": "readiness_low",
            "priority": "high",
        }

    if undertraining:
        return {
            "title": "Unterrepräsentierte Bereiche trainieren",
            "reason": undertraining[0].get(
                "message",
                ""
            ),
            "priority": "medium",
        }

    return {
        "title": "Training fortsetzen",
        "reason": (
            "Keine auffälligen Belastungssignale erkannt."
        ),
        "priority": "low",
    }