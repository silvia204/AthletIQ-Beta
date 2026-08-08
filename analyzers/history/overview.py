"""
overview.py

Erstellt eine kompakte Übersicht der Trainingshistorie.
"""

from __future__ import annotations


def analyze_overview(
    history_summary: dict,
) -> dict:
    """
    Fasst die wichtigsten Kennzahlen der Trainingshistorie zusammen.
    """

    windows = history_summary.get(
        "windows",
        {},
    )

    window_28 = windows.get(
        "28_days",
        {},
    )

    return {
        "sessions": int(
            window_28.get(
                "sessions",
                0,
            )
            or 0
        ),
        "minutes": int(
            window_28.get(
                "minutes",
                0,
            )
            or 0
        ),
        "average_rpe": window_28.get(
            "average_rpe"
        ),
        "average_score": window_28.get(
            "average_score"
        ),
        "total_score": float(
            window_28.get(
                "total_score",
                0,
            )
            or 0
        ),
        "overload_signals": len(
            history_summary.get(
                "overload_signals",
                [],
            )
        ),
        "undertraining_signals": len(
            history_summary.get(
                "undertraining_signals",
                [],
            )
        ),
    }