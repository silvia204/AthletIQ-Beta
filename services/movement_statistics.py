"""app/core/crossfit/movement_statistics.py

Statistics for CrossFit movement families across workout history.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .movement_registry import MOVEMENTS, MOVEMENT_BY_ID
from .movement_mapper import map_workout


@dataclass(frozen=True)
class MovementStatistic:
    movement_id: str
    display_name: str
    category: str
    count: int


def movement_frequency(
    workouts: Iterable[Iterable[str]],
) -> List[MovementStatistic]:
    """Count how many workouts contain each movement family."""

    counter: Counter[str] = Counter()

    for workout in workouts:
        for movement in map_workout(workout):
            counter[movement.movement_id] += 1

    stats: List[MovementStatistic] = []

    for movement_id, count in counter.most_common():
        movement = MOVEMENT_BY_ID[movement_id]
        stats.append(
            MovementStatistic(
                movement_id=movement.movement_id,
                display_name=movement.display_name,
                category=movement.category.value,
                count=count,
            )
        )

    return stats


def category_frequency(
    workouts: Iterable[Iterable[str]],
) -> Dict[str, int]:
    """Return number of movement occurrences per category."""

    counts = defaultdict(int)

    for stat in movement_frequency(workouts):
        counts[stat.category] += stat.count

    return dict(counts)


def top_movements(
    workouts: Iterable[Iterable[str]],
    limit: int = 5,
) -> List[MovementStatistic]:
    """Return the most frequently trained movement families."""

    return movement_frequency(workouts)[:limit]


def untrained_movements(
    workouts: Iterable[Iterable[str]],
) -> List[str]:
    """Return movement ids that never occurred."""

    trained = {
        stat.movement_id
        for stat in movement_frequency(workouts)
    }

    return sorted(
        movement.movement_id
        for movement in MOVEMENTS
        if movement.movement_id not in trained
    )


def dashboard_summary(
    workouts: Iterable[Iterable[str]],
) -> Dict[str, object]:
    """Compact summary for dashboard widgets."""

    return {
        "top_movements": top_movements(workouts),
        "category_frequency": category_frequency(workouts),
        "missing_movements": untrained_movements(workouts),
        "total_unique_movements": len(
            movement_frequency(workouts)
        ),
    }
