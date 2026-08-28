"""
history_normalization.py

Normalisiert Analysewerte vor der Speicherung in der
Workout-Historie.

Die Historie verwendet ausschließlich kanonische,
maschinenlesbare Keys.

Beispiele:
    MovementPattern.SQUAT -> "squat"
    "Vertical Pull"       -> "vertical_pull"
    "Horizontal Push"     -> "horizontal_push"
    "latissimus"          -> "lats"

Diese Normalisierung betrifft ausschließlich die Persistenz.
Die Analysemodelle selbst werden dadurch nicht verändert.
"""

from __future__ import annotations

from enum import Enum
import re
from typing import Any


# ---------------------------------------------------------
# EXPLIZITE FACHLICHE ALIASE
# ---------------------------------------------------------

MOVEMENT_PATTERN_ALIASES = {
    "horizontal pull": "horizontal_pull",
    "horizontal push": "horizontal_push",
    "vertical pull": "vertical_pull",
    "vertical push": "vertical_push",
    "anti rotation": "anti_rotation",
    "anti extension": "anti_extension",
    "core flexion": "core_flexion",
}


MUSCLE_GROUP_ALIASES = {
    "latissimus": "lats",
    "latissimus dorsi": "lats",
    "quads": "quadriceps",
    "front delts": "shoulders",
    "upper back": "back",
    "spinal erectors": "back",
    "trapezius": "traps",
    "abdominals": "core",
    "deep core": "core",
    "obliques": "core",
    "forearms grip": "forearms",
}


# ---------------------------------------------------------
# GENERISCHE KEY-NORMALISIERUNG
# ---------------------------------------------------------

def _to_canonical_key(value: Any) -> str:
    """
    Wandelt einen Enum- oder String-Key in einen
    kanonischen snake_case-Key um.
    """

    if isinstance(value, Enum):
        value = value.value

    text = str(value).strip()

    # CamelCase-Grenzen berücksichtigen.
    text = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])",
        "_",
        text,
    )

    text = text.replace("-", "_")
    text = text.replace(" ", "_")

    # Mehrere Unterstriche zusammenfassen.
    text = re.sub(r"_+", "_", text)

    return text.strip("_").casefold()


def _normalize_alias_lookup(value: Any) -> str:
    """
    Erzeugt eine normalisierte Form für Alias-Lookups.
    """

    if isinstance(value, Enum):
        value = value.value

    text = str(value).strip().casefold()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = re.sub(r"\s+", " ", text)

    return text


# ---------------------------------------------------------
# MOVEMENT PATTERNS
# ---------------------------------------------------------

def normalize_movement_patterns(
    values: dict[Any, Any] | None,
) -> dict[str, Any]:
    """
    Normalisiert Movement-Pattern-Keys für die Historie.
    """

    if not values:
        return {}

    result: dict[str, Any] = {}

    for raw_key, value in values.items():
        lookup_key = _normalize_alias_lookup(raw_key)

        canonical_key = MOVEMENT_PATTERN_ALIASES.get(
            lookup_key,
            _to_canonical_key(raw_key),
        )

        _merge_value(
            result,
            canonical_key,
            value,
        )

    return result


# ---------------------------------------------------------
# MUSKELGRUPPEN
# ---------------------------------------------------------

def normalize_muscle_groups(
    values: dict[Any, Any] | None,
) -> dict[str, Any]:
    """
    Normalisiert Muskelgruppen-Keys für die Historie.
    """

    if not values:
        return {}

    result: dict[str, Any] = {}

    for raw_key, value in values.items():
        lookup_key = _normalize_alias_lookup(raw_key)

        canonical_key = MUSCLE_GROUP_ALIASES.get(
            lookup_key,
            _to_canonical_key(raw_key),
        )

        _merge_value(
            result,
            canonical_key,
            value,
        )

    return result


# ---------------------------------------------------------
# MERGE
# ---------------------------------------------------------

def _merge_value(
    target: dict[str, Any],
    key: str,
    value: Any,
) -> None:
    """
    Verhindert Datenverlust, falls zwei alte Aliase auf
    denselben kanonischen Key normalisiert werden.

    Beispiel:
        {"lats": 1, "latissimus": 2}

    wird:
        {"lats": 3}
    """

    if key not in target:
        target[key] = value
        return

    existing = target[key]

    if (
        isinstance(existing, (int, float))
        and not isinstance(existing, bool)
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        target[key] = existing + value
        return

    # Bei nichtnumerischen Werten behalten wir den
    # bereits vorhandenen Wert, statt ihn still zu überschreiben.