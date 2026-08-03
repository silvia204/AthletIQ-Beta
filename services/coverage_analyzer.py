"""app/core/crossfit/coverage_analyzer.py

Analyze CrossFit movement coverage over a collection of workouts.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

from .athlete_level import (
    AthleteLevel,
    coverage_percentage,
    expected_ids,
)
from .movement_mapper import movement_ids
from .crossfit_movements import MOVEMENTS, CrossFitMovement


@dataclass(frozen=True)
class CoverageReport:
    athlete_level: AthleteLevel
    completed: Set[str]
    expected: Set[str]
    missing: Set[str]
    coverage: float
    by_category: Dict[str, List[str]]


def analyze_workouts(
    workouts: Iterable[Iterable[str]],
    athlete_level: AthleteLevel,
) -> CoverageReport:
    """
    Analyze movement coverage for multiple workouts.

    Args:
        workouts:
            Iterable of workouts. Each workout is an iterable of exercise names.
    """

    completed: Set[str] = set()

    for workout in workouts:
        completed.update(movement_ids(workout))

    expected = expected_ids(athlete_level)
    missing = expected - completed

    grouped: Dict[str, List[str]] = defaultdict(list)

    for movement_id in sorted(completed):
        movement: CrossFitMovement | None = MOVEMENTS.get(movement_id)
        if movement is None:
            continue
        grouped[movement.category.value].append(movement.display_name)

    for values in grouped.values():
        values.sort()

    return CoverageReport(
        athlete_level=athlete_level,
        completed=completed,
        expected=expected,
        missing=missing,
        coverage=coverage_percentage(completed, athlete_level),
        by_category=dict(grouped),
    )


def missing_movements(report: CoverageReport) -> List[CrossFitMovement]:
    """Return missing movement families."""

    return sorted(
        (
            MOVEMENTS[mid]
            for mid in report.missing
            if mid in MOVEMENTS
        ),
        key=lambda m: (m.category.value, m.display_name),
    )


def completed_movements(report: CoverageReport) -> List[CrossFitMovement]:
    """Return completed movement families."""

    return sorted(
        (
            MOVEMENTS[mid]
            for mid in report.completed
            if mid in MOVEMENTS
        ),
        key=lambda m: (m.category.value, m.display_name),
    )
