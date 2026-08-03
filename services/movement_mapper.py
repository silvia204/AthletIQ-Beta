"""
movement_mapper.py

Maps parsed workout exercises to CrossFit movement families.
"""

from __future__ import annotations

from typing import Iterable

from .crossfit_movements import (
    CrossFitMovement,
    find_movement,
)


def map_workout(
    exercises: Iterable[str],
) -> list[CrossFitMovement]:
    """
    Maps exercise names to CrossFit movement families.

    Duplicate movement families are removed while preserving order.
    """

    mapped: list[CrossFitMovement] = []
    seen: set[str] = set()

    for exercise in exercises:

        movement = find_movement(exercise)

        if movement is None:
            continue

        if movement.movement_id in seen:
            continue

        seen.add(movement.movement_id)
        mapped.append(movement)

    return mapped


def movement_ids(
    exercises: Iterable[str],
) -> list[str]:
    """Return mapped movement ids."""

    return [
        movement.movement_id
        for movement in map_workout(exercises)
    ]


def unknown_exercises(
    exercises: Iterable[str],
) -> list[str]:
    """Return exercises that cannot be mapped."""

    unknown: list[str] = []

    for exercise in exercises:

        if find_movement(exercise) is None:
            unknown.append(exercise)

    return unknown