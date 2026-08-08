"""
trends.py

Liefert die Trendinformationen der Trainingshistorie.
"""

from __future__ import annotations


def analyze_trends(
    history_summary: dict,
) -> dict:
    """
    Gibt die vorhandenen Trendinformationen
    der Trainingshistorie zurück.
    """

    windows = history_summary.get(
        "windows",
        {},
    )

    return {
        "windows": windows,
        "load_change_percent": history_summary.get(
            "belastungsveraenderung_prozent"
        ),
        "last_7_day_load": history_summary.get(
            "belastung_letzte_7_tage"
        ),
        "previous_7_day_load": history_summary.get(
            "belastung_vorherige_7_tage"
        ),
    }