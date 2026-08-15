"""
top_findings.py

Fasst die wichtigsten Erkenntnisse der Trainingshistorie zusammen.
"""

from __future__ import annotations

def analyze_top_findings(
    *,
    readiness: dict,
    weekly_focus: dict,
    trends: dict,
    overview: dict,
    movement_coverage: dict,
) -> list[dict]:
    """
    Erstellt eine priorisierte Liste der wichtigsten
    Erkenntnisse.
    """

    findings: list[dict] = []

    # Readiness
    if readiness.get("status") == "low":
        findings.append(
            {
                "type": "readiness",
                "priority": 1,
                "title": "Trainingsbereitschaft reduziert",
                "details": readiness,
            }
        )

    # Weekly Focus
    if weekly_focus:
        findings.append(
            {
                "type": "weekly_focus",
                "priority": 2,
                "title": weekly_focus.get(
                    "title",
                    "Wochenschwerpunkt",
                ),
                "details": weekly_focus,
            }
        )

    # Coverage
    coverage = float(
        movement_coverage.get(
            "coverage_percent",
            0.0,
        )
        or 0.0
    )

    findings.append(
        {
            "type": "movement_coverage",
            "priority": 3,
            "title": (
                f"Movement Coverage: {coverage:.1f}%"
            ),
            "details": movement_coverage,
        }
    )

    findings.sort(
        key=lambda item: item["priority"]
    )

    return findings