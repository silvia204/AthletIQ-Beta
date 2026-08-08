"""app/core/crossfit/athlete_level.py

Defines athlete levels and helper functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

from .movement_registry import AthleteLevel, Movement, MOVEMENTS

_LEVEL_ORDER = {
    AthleteLevel.BEGINNER: 0,
    AthleteLevel.SCALED: 1,
    AthleteLevel.ADVANCED: 2,
}


@dataclass(frozen=True)
class AthleteProfile:
    """Represents an athlete profile."""

    level: AthleteLevel

    @property
    def expected_movements(self) -> List[Movement]:
        return expected_movements(self.level)

    def missing_movements(
        self,
        completed_movements: Set[str],
    ) -> List[Movement]:
        return [
            movement
            for movement in self.expected_movements
            if movement.movement_id not in completed_movements
        ]


def expected_movements(level: AthleteLevel) -> List[Movement]:
    current = _LEVEL_ORDER[level]
    return sorted(
        [
            movement
            for movement in MOVEMENTS
            if _LEVEL_ORDER[movement.minimum_level] <= current
        ],
        key=lambda m: (m.category.value, m.display_name),
    )


def expected_ids(level: AthleteLevel) -> Set[str]:
    return {m.movement_id for m in expected_movements(level)}


def movement_is_expected(movement_id: str, level: AthleteLevel) -> bool:
    return movement_id in expected_ids(level)


def missing_movement_ids(
    completed_movements: Set[str],
    level: AthleteLevel,
) -> Set[str]:
    return expected_ids(level) - completed_movements


def coverage_percentage(
    completed_movements: Set[str],
    level: AthleteLevel,
) -> float:
    expected = expected_ids(level)
    if not expected:
        return 100.0
    completed = len(expected & completed_movements)
    return round(completed / len(expected) * 100, 1)
