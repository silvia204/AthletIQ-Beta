\
"""app/parser/workout_parser.py

Simple parser for CrossFit workouts.

Version 1.0 intentionally focuses on extracting exercises and mapping
them to CrossFit movement families. More advanced parsing (rounds,
weights, EMOM, AMRAP, etc.) will be added later.
"""

from __future__ import annotations
from enum import Enum

import re
from dataclasses import dataclass, field
from typing import List, Optional

from services.movement_mapper import map_workout
from services.crossfit_movements import CrossFitMovement


@dataclass(frozen=True)
class ExerciseEntry:
    raw_text: str
    reps: Optional[int]
    weight: Optional[str]
    exercise: str


@dataclass
class ParsedWorkout:
    original_text: str
    exercises: List[ExerciseEntry] = field(default_factory=list)
    movements: List[CrossFitMovement] = field(default_factory=list)


_REPS = re.compile(r"^\s*(\d+)\s+(.+)$")
_WEIGHT = re.compile(r"(.+?)\s*\(([^)]+)\)$")


def _parse_line(line: str) -> Optional[ExerciseEntry]:
    line = line.strip()

    if not line:
        return None

    # Ignore common workout headers
    ignored = (
        "amrap",
        "emom",
        "for time",
        "every",
        "rest",
        "round",
        "rounds",
    )

    if line.lower().startswith(ignored):
        return None

    reps = None
    weight = None
    exercise = line

    match = _REPS.match(line)
    if match:
        reps = int(match.group(1))
        exercise = match.group(2)

    match = _WEIGHT.match(exercise)
    if match:
        exercise = match.group(1).strip()
        weight = match.group(2).strip()

    return ExerciseEntry(
        raw_text=line,
        reps=reps,
        weight=weight,
        exercise=exercise.strip(),
    )


def parse_workout(text: str) -> ParsedWorkout:
    """
    Parse a workout description into structured data.

    Unterstützt sowohl mehrzeilige Workouts als auch
    einzeilige Google-Sheet-Einträge wie:

    Strength Deadlifts: 4x4 Deadlifts |
    5 RFT: 250m Row, 10 Burpees, 5 Deadlifts
    """

    parsed = ParsedWorkout(original_text=text)

    # Vereinheitliche typische Trenner
    normalized = (
        text.replace(" | ", "\n")
            .replace("|", "\n")
            .replace(",", "\n")
            .replace(";", "\n")
    )

    # Zerlege zusätzlich an Doppelpunkten
    fragments: list[str] = []

    for line in normalized.splitlines():

        line = line.strip()

        if not line:
            continue

        if ":" in line:
            fragments.extend(
                part.strip()
                for part in line.split(":")
                if part.strip()
            )
        else:
            fragments.append(line)

    # Offensichtliche Workout-Überschriften ignorieren
    ignored_prefixes = (
        "strength",
        "warm up",
        "warm-up",
        "cool down",
        "cool-down",
        "skill",
        "accessory",
        "metcon",
        "workout",
        "amrap",
        "emom",
        "for time",
        "rft",
    )

    cleaned_fragments: list[str] = []

    for fragment in fragments:

        lower = fragment.casefold()

        if lower.startswith(ignored_prefixes):
            continue

        # "5 RFT" oder "3 Runden" entfernen
        fragment = re.sub(
            r"^\d+\s*(rft|rounds?|runden)\b[:\s-]*",
            "",
            fragment,
            flags=re.IGNORECASE,
        ).strip()

        if fragment:
            cleaned_fragments.append(fragment)

    for fragment in cleaned_fragments:

        exercise = _parse_line(fragment)

        if exercise:
            parsed.exercises.append(exercise)

    parsed.movements = map_workout(
        [entry.exercise for entry in parsed.exercises]
    )

    return parsed


def detected_exercises(parsed: ParsedWorkout) -> List[str]:
    return [e.exercise for e in parsed.exercises]


def detected_movements(parsed: ParsedWorkout) -> List[str]:
    return [m.display_name for m in parsed.movements]
