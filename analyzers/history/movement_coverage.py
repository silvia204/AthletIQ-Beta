"""
movement_coverage.py

Analysiert die CrossFit-Movement-Coverage.
"""

from __future__ import annotations


def analyze_movement_coverage(
    history_summary: dict,
) -> dict:
    """
    Liefert die vorhandene Movement-Coverage
    der Trainingshistorie.
    """

    coverage = history_summary.get(
        "crossfit_coverage",
        {}
    )

    return {
        "athlete_level": coverage.get(
            "athlete_level"
        ),
        "coverage_percent": float(
            coverage.get(
                "coverage_percent",
                0.0,
            )
            or 0.0
        ),
        "covered": int(
            coverage.get(
                "covered",
                0,
            )
            or 0
        ),
        "expected": int(
            coverage.get(
                "expected",
                0,
            )
            or 0
        ),
        "missing": history_summary.get(
            "missing_crossfit_movements",
            [],
        ),
        "completed": history_summary.get(
            "crossfit_movements",
            {},
        ),
    }