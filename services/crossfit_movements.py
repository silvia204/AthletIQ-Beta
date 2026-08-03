"""
SportCoach App
Module: crossfit_movements.py

Version: 1.0.0
Status: Production Ready

This module is the single source of truth for all CrossFit movement
families used by the SportCoach application.

Every parser, analyzer and dashboard component must reference this
module instead of maintaining its own movement definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple


# ============================================================================
# ENUMS
# ============================================================================

class AthleteLevel(str, Enum):
    """Supported athlete levels."""

    BEGINNER = "Beginner"
    SCALED = "Scaled"
    ADVANCED = "Advanced"


class MovementCategory(str, Enum):
    """Main CrossFit movement categories."""

    WEIGHTLIFTING = "Weightlifting"
    GYMNASTICS = "Gymnastics"
    MONOSTRUCTURAL = "Monostructural"
    FUNCTIONAL = "Functional"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass(frozen=True)
class CrossFitMovement:
    """
    Represents one CrossFit movement family.

    Example:

    Snatch
        • Power Snatch
        • Hang Power Snatch
        • Hang Snatch
        • Squat Snatch
        • Muscle Snatch
        • Dumbbell Snatch

    All variants belong to the same movement family.
    """

    movement_id: str

    display_name: str

    category: MovementCategory

    minimum_level: AthleteLevel

    variants: Tuple[str, ...]

    aliases: Tuple[str, ...]

    notes: str = ""

    @property
    def canonical_name(self) -> str:
        return self.display_name

    def matches(self, exercise: str) -> bool:
        """
        Returns True if the supplied exercise belongs
        to this movement family.
        """

        normalized = normalize_name(exercise)

        if normalized == normalize_name(self.display_name):
            return True

        for variant in self.variants:
            if normalized == normalize_name(variant):
                return True

        for alias in self.aliases:
            if normalized == normalize_name(alias):
                return True

        return False


# ============================================================================
# NORMALIZATION
# ============================================================================

def normalize_name(text: str) -> str:
    """
    Normalizes exercise names.

    Examples

    Power-Clean
    power clean
    POWER CLEAN

    →

    power clean
    """

    text = text.lower().strip()

    replacements = {
        "-": " ",
        "_": " ",
        "&": "and",
        "  ": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    while "  " in text:
        text = text.replace("  ", " ")

    return text


# ============================================================================
# LOOKUP TABLES
# ============================================================================

MOVEMENTS: List[CrossFitMovement] = []

MOVEMENT_BY_ID: Dict[str, CrossFitMovement] = {}

MOVEMENT_BY_ALIAS: Dict[str, CrossFitMovement] = {}

MOVEMENT_BY_VARIANT: Dict[str, CrossFitMovement] = {}


# ============================================================================
# INTERNAL REGISTRATION
# ============================================================================

def register(movement: CrossFitMovement) -> None:
    """
    Registers a movement family and automatically builds
    all lookup dictionaries.
    """

    if movement.movement_id in MOVEMENT_BY_ID:
        raise ValueError(
            f"Duplicate movement id: {movement.movement_id}"
        )

    MOVEMENTS.append(movement)

    MOVEMENT_BY_ID[movement.movement_id] = movement

    MOVEMENT_BY_ALIAS[
        normalize_name(movement.display_name)
    ] = movement

    for alias in movement.aliases:
        key = normalize_name(alias)

        existing = MOVEMENT_BY_ALIAS.get(key)

        if existing is not None:

            # Alias gehört bereits zu demselben Movement.
            # Kein Fehler – einfach überspringen.
            if existing.movement_id == movement.movement_id:
                continue

            # Alias gehört zu einem anderen Movement.
            raise ValueError(
                f"Duplicate alias '{alias}' "
                f"used by '{existing.display_name}' "
                f"and '{movement.display_name}'."
            )

        MOVEMENT_BY_ALIAS[key] = movement

    for variant in movement.variants:
        key = normalize_name(variant)

        existing = MOVEMENT_BY_VARIANT.get(key)

        if existing is not None:

            if existing.movement_id == movement.movement_id:
                continue

            raise ValueError(
                f"Duplicate variant '{variant}' "
                f"used by '{existing.display_name}' "
                f"and '{movement.display_name}'."
            )

        MOVEMENT_BY_VARIANT[key] = movement


# ============================================================================
# PUBLIC API
# ============================================================================

def all_movements() -> Tuple[CrossFitMovement, ...]:
    """Returns every registered movement family."""

    return tuple(MOVEMENTS)


def get_movement(movement_id: str) -> Optional[CrossFitMovement]:
    """Returns a movement by its id."""

    return MOVEMENT_BY_ID.get(movement_id)


def find_movement(exercise_name: str) -> Optional[CrossFitMovement]:
    """
    Finds the movement family belonging to an exercise.

    Example

    Hang Power Snatch

    →

    Snatch
    """

    key = normalize_name(exercise_name)

    if key in MOVEMENT_BY_ALIAS:
        return MOVEMENT_BY_ALIAS[key]

    if key in MOVEMENT_BY_VARIANT:
        return MOVEMENT_BY_VARIANT[key]

    return None


def movements_for_level(
    level: AthleteLevel,
) -> Tuple[CrossFitMovement, ...]:
    """
    Returns all movement families expected for the
    specified athlete level.
    """

    order = {
        AthleteLevel.BEGINNER: 0,
        AthleteLevel.SCALED: 1,
        AthleteLevel.ADVANCED: 2,
    }

    current = order[level]

    return tuple(
        movement
        for movement in MOVEMENTS
        if order[movement.minimum_level] <= current
    )

# ============================================================================
# WEIGHTLIFTING
# ============================================================================

register(
    CrossFitMovement(
        movement_id="squat",
        display_name="Squat",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Air Squat",
            "Goblet Squat",
            "Front Squat",
            "Back Squat",
            "Overhead Squat",
            "Pause Squat",
        ),
        aliases=(
            "air squat",
            "goblet squat",
            "front squat",
            "back squat",
            "overhead squat",
            "ohs",
            "pause squat",
        ),
        notes="Tracks all squat variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="deadlift",
        display_name="Deadlift",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Deadlift",
            "Romanian Deadlift",
            "Sumo Deadlift",
            "Single Leg Deadlift",
            "Trap Bar Deadlift",
        ),
        aliases=(
            "dl",
            "romanian deadlift",
            "rdl",
            "sumo deadlift",
            "single leg deadlift",
            "trap bar deadlift",
        ),
        notes="Tracks all deadlift variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="clean",
        display_name="Clean",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Power Clean",
            "Hang Power Clean",
            "Hang Clean",
            "Squat Clean",
            "Muscle Clean",
            "Clean & Jerk",
            "DB Clean",
        ),
        aliases=(
            "power clean",
            "hang power clean",
            "hang clean",
            "squat clean",
            "muscle clean",
            "clean and jerk",
            "clean & jerk",
            "db clean",
            "dumbbell clean",
        ),
        notes="Tracks the complete clean movement family.",
    )
)

register(
    CrossFitMovement(
        movement_id="snatch",
        display_name="Snatch",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "PVC Snatch",
            "Power Snatch",
            "Hang Power Snatch",
            "Hang Snatch",
            "Squat Snatch",
            "Muscle Snatch",
            "DB Snatch",
        ),
        aliases=(
            "power snatch",
            "hang power snatch",
            "hang snatch",
            "hang squat snatch",
            "squat snatch",
            "muscle snatch",
            "db snatch",
            "dumbbell snatch",
        ),
        notes="Tracks the complete snatch movement family.",
    )
)

register(
    CrossFitMovement(
        movement_id="jerk",
        display_name="Jerk",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Push Jerk",
            "Split Jerk",
            "Power Jerk",
        ),
        aliases=(
            "push jerk",
            "split jerk",
            "power jerk",
        ),
        notes="Tracks all jerk variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="thruster",
        display_name="Thruster",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Thruster",
            "DB Thruster",
            "Single DB Thruster",
        ),
        aliases=(
            "db thruster",
            "dumbbell thruster",
            "single db thruster",
        ),
        notes="Tracks all thruster variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="wall_ball",
        display_name="Wall Ball",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Wall Ball",
            "Heavy Wall Ball",
            "Wall Ball Shot",
        ),
        aliases=(
            "wall balls",
            "wall ball shot",
            "heavy wall ball",
        ),
        notes="Tracks all wall ball variations.",
    )
)

# ============================================================================
# FUNCTIONAL
# ============================================================================

register(
    CrossFitMovement(
        movement_id="burpee",
        display_name="Burpee",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Burpee",
            "Burpee Over Bar",
            "Bar Facing Burpee",
            "Burpee Box Jump",
            "Burpee Box Jump Over",
        ),
        aliases=(
            "bar facing burpee",
            "burpee over bar",
            "burpee box jump",
            "burpee box jump over",
            "bbjo",
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="box_jump",
        display_name="Box Jump",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Box Step Up",
            "Box Jump",
            "Box Jump Over",
        ),
        aliases=(
            "box step up",
            "box jump over",
            "bjo",
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="carry",
        display_name="Carry",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Farmer Carry",
            "Front Rack Carry",
            "Overhead Carry",
            "Suitcase Carry",
            "Sandbag Carry",
        ),
        aliases=(
            "farmer carry",
            "farmers carry",
            "front rack carry",
            "overhead carry",
            "suitcase carry",
            "sandbag carry",
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="lunge",
        display_name="Lunge",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Walking Lunge",
            "Reverse Lunge",
            "Forward Lunge",
            "Overhead Lunge",
            "DB Walking Lunge",
        ),
        aliases=(
            "walking lunge",
            "reverse lunge",
            "forward lunge",
            "overhead lunge",
            "db walking lunge",
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="sled",
        display_name="Sled",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Sled Push",
            "Sled Pull",
        ),
        aliases=(
            "sled push",
            "sled pull",
        ),
    )
)

# ============================================================================
# GYMNASTICS
# ============================================================================

register(
    CrossFitMovement(
        movement_id="push_up",
        display_name="Push-up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Wall Push-up",
            "Incline Push-up",
            "Knee Push-up",
            "Push-up",
            "Hand Release Push-up",
            "Deficit Push-up",
            "Ring Push-up",
        ),
        aliases=(
            "wall push up",
            "incline push up",
            "knee push up",
            "hand release push up",
            "hr push up",
            "deficit push up",
            "ring push up",
        ),
        notes="Tracks all push-up variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="pull_up",
        display_name="Pull-up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Ring Row",
            "Band Pull-up",
            "Jumping Pull-up",
            "Pull-up",
            "Strict Pull-up",
            "Kipping Pull-up",
        ),
        aliases=(
            "ring row",
            "band pull up",
            "banded pull up",
            "jumping pull up",
            "strict pull up",
            "kipping pull up",
        ),
        notes="Tracks the complete pull-up progression.",
    )
)

register(
    CrossFitMovement(
        movement_id="chest_to_bar",
        display_name="Chest-to-Bar",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Chest-to-Bar Pull-up",
            "Strict Chest-to-Bar",
            "Butterfly Chest-to-Bar",
        ),
        aliases=(
            "ctb",
            "c2b",
            "strict chest to bar",
            "butterfly chest to bar",
        ),
        notes="Advanced pulling movement.",
    )
)

register(
    CrossFitMovement(
        movement_id="muscle_up",
        display_name="Muscle-up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Bar Muscle-up",
            "Strict Bar Muscle-up",
            "Ring Muscle-up",
            "Strict Ring Muscle-up",
        ),
        aliases=(
            "bar muscle up",
            "bar mu",
            "ring muscle up",
            "ring mu",
            "strict bar muscle up",
            "strict ring muscle up",
        ),
        notes="Tracks both bar and ring muscle-ups.",
    )
)

register(
    CrossFitMovement(
        movement_id="handstand",
        display_name="Handstand",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Wall Handstand Hold",
            "Freestanding Handstand",
            "Wall Walk",
        ),
        aliases=(
            "wall handstand",
            "handstand hold",
            "wall handstand hold",
            "wall walk",
        ),
        notes="Scaled athletes are expected to master the wall version.",
    )
)

register(
    CrossFitMovement(
        movement_id="handstand_push_up",
        display_name="Handstand Push-up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Box Handstand Push-up",
            "Strict Handstand Push-up",
            "Kipping Handstand Push-up",
            "Deficit Handstand Push-up",
        ),
        aliases=(
            "hspu",
            "strict hspu",
            "kipping hspu",
            "deficit hspu",
            "box hspu",
        ),
        notes="Advanced gymnastics movement.",
    )
)

register(
    CrossFitMovement(
        movement_id="handstand_walk",
        display_name="Handstand Walk",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Handstand Walk",
        ),
        aliases=(
            "hs walk",
            "hsw",
        ),
        notes="Only expected for advanced athletes.",
    )
)

register(
    CrossFitMovement(
        movement_id="toes_to_bar",
        display_name="Toes-to-Bar",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Hanging Knee Raise",
            "Hanging Leg Raise",
            "Toes-to-Bar",
            "Strict Toes-to-Bar",
        ),
        aliases=(
            "ttb",
            "knee raise",
            "hanging knee raise",
            "leg raise",
            "hanging leg raise",
            "strict toes to bar",
        ),
        notes="Tracks the complete hanging core progression.",
    )
)

register(
    CrossFitMovement(
        movement_id="rope_climb",
        display_name="Rope Climb",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Assisted Rope Climb",
            "Rope Climb",
            "Legless Rope Climb",
        ),
        aliases=(
            "legless rope climb",
            "assisted rope climb",
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="ring_dip",
        display_name="Ring Dip",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Bench Dip",
            "Ring Dip",
            "Strict Ring Dip",
        ),
        aliases=(
            "bench dip",
            "strict ring dip",
            "dip",
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="pistols",
        display_name="Pistols",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Assisted Pistol",
            "Pistol Squat",
            "Weighted Pistol",
        ),
        aliases=(
            "pistol",
            "pistol squat",
            "single leg squat",
            "weighted pistol",
            "assisted pistol",
        ),
        notes="Single-leg squat progression.",
    )
)

# ============================================================================
# MONOSTRUCTURAL
# ============================================================================

register(
    CrossFitMovement(
        movement_id="run",
        display_name="Run",
        category=MovementCategory.MONOSTRUCTURAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Walk",
            "Jog",
            "Run",
            "Sprint",
            "Shuttle Run",
        ),
        aliases=(
            "walk",
            "jog",
            "running",
            "sprint",
            "shuttle run",
            "400m run",
            "800m run",
            "1600m run",
            "1 mile run",
        ),
        notes="All running variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="row",
        display_name="Row",
        category=MovementCategory.MONOSTRUCTURAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Row",
            "Concept2 Row",
            "Erg Row",
        ),
        aliases=(
            "rowing",
            "row erg",
            "erg row",
            "concept2 row",
            "c2 row",
        ),
        notes="RowErg / Concept2 rowing.",
    )
)

register(
    CrossFitMovement(
        movement_id="ski",
        display_name="Ski",
        category=MovementCategory.MONOSTRUCTURAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Ski",
            "SkiErg",
        ),
        aliases=(
            "skierg",
            "ski erg",
        ),
        notes="Concept2 SkiErg.",
    )
)

register(
    CrossFitMovement(
        movement_id="bike",
        display_name="Bike",
        category=MovementCategory.MONOSTRUCTURAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Bike",
            "BikeErg",
            "Assault Bike",
            "Echo Bike",
        ),
        aliases=(
            "bikeerg",
            "bike erg",
            "assault bike",
            "echo bike",
            "air bike",
        ),
        notes="All bike ergometers.",
    )
)

register(
    CrossFitMovement(
        movement_id="jump_rope",
        display_name="Jump Rope",
        category=MovementCategory.MONOSTRUCTURAL,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Single Under",
            "Double Under",
            "Triple Under",
        ),
        aliases=(
            "single under",
            "single unders",
            "su",
            "double under",
            "double unders",
            "du",
            "triple under",
            "triple unders",
        ),
        notes=(
            "Beginner: Single Unders\n"
            "Scaled: Double Unders\n"
            "Advanced: Double Unders should be mastered."
        ),
    )
)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Freeze movement collection
MOVEMENTS = tuple(MOVEMENTS)

# ============================================================================
# VALIDATION
# ============================================================================

def validate_database() -> None:
    """
    Validate movement database consistency.

    Raises
    ------
    ValueError
        If duplicate aliases, variants or IDs are detected.
    """

    ids = set()

    for movement in MOVEMENTS:

        if movement.movement_id in ids:
            raise ValueError(
                f"Duplicate movement id: {movement.movement_id}"
            )

        ids.add(movement.movement_id)

        if not movement.variants:
            raise ValueError(
                f"{movement.display_name} has no variants."
            )

        if not movement.aliases:
            raise ValueError(
                f"{movement.display_name} has no aliases."
            )


# Validate once during import
validate_database()

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "AthleteLevel",
    "MovementCategory",
    "CrossFitMovement",
    "MOVEMENTS",
    "MOVEMENT_BY_ID",
    "MOVEMENT_BY_ALIAS",
    "MOVEMENT_BY_VARIANT",
    "register",
    "normalize_name",
    "find_movement",
    "get_movement",
    "movements_for_level",
    "all_movements",
]