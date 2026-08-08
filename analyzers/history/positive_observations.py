"""
positive_observations.py

Erkennt positive Aspekte der bisherigen Trainingshistorie.
"""

from __future__ import annotations


def analyze_positive_observations(
    *,
    history_summary: dict,
    readiness: dict,
    movement_coverage: dict,
) -> list[dict]:
    """
    Fasst positive Beobachtungen der Trainingshistorie zusammen.
    """

    observations: list[dict] = []

    readiness_status = readiness.get(
        "status",
        "high",
    )

    if readiness_status == "high":
        observations.append(
            {
                "code": "good_readiness",
                "title": "Hohe Trainingsbereitschaft",
                "message": (
                    "Es wurden aktuell keine relevanten "
                    "Überlastungssignale erkannt."
                ),
            }
        )

    coverage = float(
        movement_coverage.get(
            "coverage_percent",
            0.0,
        )
        or 0.0
    )

    if coverage >= 80:
        observations.append(
            {
                "code": "good_movement_coverage",
                "title": "Breite Movement-Abdeckung",
                "message": (
                    "Ein großer Teil der erwarteten "
                    "CrossFit-Movements wurde bereits trainiert."
                ),
            }
        )

    sessions = (
        history_summary.get("windows", {})
        .get("28_days", {})
        .get("sessions", 0)
    )

    if sessions >= 8:
        observations.append(
            {
                "code": "good_consistency",
                "title": "Konsequentes Training",
                "message": (
                    "In den letzten 28 Tagen wurden "
                    "regelmäßig Trainingseinheiten durchgeführt."
                ),
            }
        )

    return observations