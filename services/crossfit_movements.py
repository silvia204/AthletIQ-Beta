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
from typing import Dict, Iterable, List, Optional, Tuple, Any


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

class MovementPattern(str, Enum):
   # Lower Body
    SQUAT = "Squat"
    HINGE = "Hinge"
    LUNGE = "Lunge"

    # Upper Body
    HORIZONTAL_PUSH = "Horizontal Push"
    HORIZONTAL_PULL = "Horizontal Pull"
    VERTICAL_PUSH = "Vertical Push"
    VERTICAL_PULL = "Vertical Pull"

    # Trunk
    ROTATION = "Rotation"
    CORE_FLEXION = "Core Flexion"

    # Functional
    CARRY = "Carry"
    LOCOMOTION = "Locomotion"


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

    movement_patterns: Tuple[MovementPattern, ...] = ()

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
    Deadlifts
    Burpees
    Pull-Ups

    →

    power clean
    deadlift
    burpee
    pull up
    """

    import re

    text = text.lower().strip()

    replacements = {
        "-": " ",
        "_": " ",
        "&": "and",
        "(": " ",
        ")": " ",
        ",": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    while "  " in text:
        text = text.replace("  ", " ")

    # Führende Zahlen entfernen
    # 10 Burpees -> Burpees
    # 250m Row -> Row
    text = re.sub(
        r"^\d+\s*x\s*\d+\s*",
        "",
        text,
    )

    text = re.sub(
        r"^\d+(?:/\d+)?\s*(?:kg|lb|m|km|cal|cals|sec|s|min)?\s+",
        "",
        text,
    )

    # Distanzangaben vor Monostructural-Movements entfernen
    text = re.sub(
        r"^\d+(?:\.\d+)?\s*(?:m|meter|km|mile|miles)\s+",
        "",
        text,
    )

    # Kalorienangaben entfernen
    text = re.sub(
        r"^\d+\s*(?:cal|cals)\s+",
        "",
        text,
    )

    # Zeitangaben entfernen
    text = re.sub(
        r"^\d+\s*(?:sec|secs|second|seconds|min|mins|minute|minutes)\s+",
        "",
        text,
    )

    return text.strip()


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

def movement_pattern_key(
    pattern: MovementPattern,
) -> str:
    return pattern.name.lower()

def movement_patterns_to_classification(
    movement: CrossFitMovement,
) -> list[dict[str, Any]]:
    """
    Konvertiert die hinterlegten Movement Patterns in das
    Klassifikationsformat der App.
    """

    if not movement.movement_patterns:
        return []

    contribution = round(
        1 / len(movement.movement_patterns),
        3,
    )

    return [
        {
            "type": pattern.name.lower(),
            "role": "primary",
            "contribution": contribution,
        }
        for pattern in movement.movement_patterns
    ]

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
            "Air Squats",
            "Goblet Squat",
            "Goblet Squats",
            "Front Squat",
            "Front Squats",
            "Back Squat",
            "Back Squats",
            "Overhead Squat",
            "Overhead Squats",
            "Pause Squat",
            "Pause Squats",
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
        movement_patterns=(
            MovementPattern.SQUAT,
        ),
        notes="Tracks all squat variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="clean_and_jerk",
        display_name="Clean & Jerk",
        category=MovementCategory.WEIGHTLIFTING,
        minimum_level=AthleteLevel.SCALED,

        variants=(
            "Clean & Jerk",
            "Clean & Jerks",
            "Clean and Jerk",
            "Clean and Jerks",
            "Squat Clean & Jerk",
            "Squat Clean & Jerks",
            "Squat Clean and Jerk",
            "Squat Clean and Jerks",
            "Power Clean & Jerk",
            "Power Clean & Jerks",
            "Power Clean and Jerk",
            "Power Clean and Jerks",
        ),

        aliases=(
            "C&J",
            "CJ",
        ),

        movement_patterns=(
            MovementPattern.HINGE,
            MovementPattern.SQUAT,
            MovementPattern.VERTICAL_PUSH,
        ),

        notes="Olympic lift consisting of a clean followed by a jerk.",
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
            "Deadlifts",
            "Romanian Deadlift",
            "Romanian Deadlifts",
            "Sumo Deadlift",
            "Sumo Deadlifts",
            "Single Leg Deadlift",
            "Single Leg Deadlifts",
            "Trap Bar Deadlift",
            "Trap Bar Deadlifts",
        ),
        aliases=(
            "dl",
            "romanian deadlift",
            "rdl",
            "sumo deadlift",
            "single leg deadlift",
            "trap bar deadlift",
        ),
        movement_patterns=(
            MovementPattern.HINGE,
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
            "Clean",
            "Cleans",
            "Power Clean",
            "Power Cleans",
            "Hang Power Clean",
            "Hang Power Cleans",
            "Hang Clean",
            "Hang Cleans",
            "Squat Clean",
            "Squat Cleans",
            "Muscle Clean",
            "Muscle Cleans",
            "DB Clean",
            "DB Cleans",
            "Dumbbell Clean",
            "Dumbbell Cleans",
        ),
        aliases=(
            "pc",
            "hc",
        ),
        movement_patterns=(
            MovementPattern.HINGE,
            MovementPattern.SQUAT,
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
            "Snatch",
            "Snatches",
            "PVC Snatch",
            "PVC Snatches",
            "Power Snatch",
            "Power Snatches",
            "Hang Power Snatch",
            "Hang Power Snatches",
            "Hang Snatch",
            "Hang Snatches",
            "Squat Snatch",
            "Squat Snatches",
            "Muscle Snatch",
            "Muscle Snatches",
            "DB Snatch",
            "DB Snatches",
            "Dumbbell Snatch",
            "Dumbbell Snatches",
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
        movement_patterns=(
            MovementPattern.HINGE,
            MovementPattern.SQUAT,
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
            "Jerk",
            "Jerks",
            "Push Jerk",
            "Push Jerks",
            "Split Jerk",
            "Split Jerks",
            "Power Jerk",
            "Power Jerks",
        ),
        aliases=(
            "push jerk",
            "split jerk",
            "power jerk",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PUSH,
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
            "Thrusters",
            "DB Thruster",
            "DB Thrusters",
            "Single DB Thruster",
            "Single DB Thrusters",
            "Dumbbell Thruster",
            "Dumbbell Thrusters",
        ),
        aliases=(
            "db thruster",
            "dumbbell thruster",
            "single db thruster",
        ),
        movement_patterns=(
            MovementPattern.SQUAT,
            MovementPattern.VERTICAL_PUSH,
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
            "Wall Balls",
            "Heavy Wall Ball",
            "Heavy Wall Balls",
            "Wall Ball Shot",
            "Wall Ball Shots",
        ),
        aliases=(
            "wall balls",
            "wall ball shot",
            "heavy wall ball",
        ),
        movement_patterns=(
            MovementPattern.SQUAT,
            MovementPattern.VERTICAL_PUSH,
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
            "Burpees",
            "Burpee Over Bar",
            "Burpee Over Bars",
            "Bar Facing Burpee",
            "Bar Facing Burpees",
            "Burpee Box Jump",
            "Burpee Box Jumps",
            "Burpee Box Jump Over",
            "Burpee Box Jump Overs",
        ),
        aliases=(
            "bar facing burpee",
            "burpee over bar",
            "burpee box jump",
            "burpee box jump over",
            "bbjo",
        ),
        movement_patterns=(
            MovementPattern.SQUAT,
            MovementPattern.HORIZONTAL_PUSH,
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
            "Box Step Ups",
            "Box Step Over",
            "Box Step Overs",
            "Box Jump",
            "Box Jumps",
            "Box Jump Over",
            "Box Jump Overs",
        ),
        aliases=(
            "box step up",
            "box step over",
            "box jump over",
            "bjo",
        ),
        movement_patterns=(
            MovementPattern.SQUAT,
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
            "Farmer Carries",
            "Front Rack Carry",
            "Front Rack Carries",
            "Overhead Carry",
            "Overhead Carries",
            "Suitcase Carry",
            "Suitcase Carries",
            "Sandbag Carry",
            "Sandbag Carries",
        ),
        aliases=(
            "farmer carry",
            "farmers carry",
            "front rack carry",
            "overhead carry",
            "suitcase carry",
            "sandbag carry",
        ),
        movement_patterns=(
            MovementPattern.CARRY,
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
            "Walking Lunges",
            "Reverse Lunge",
            "Reverse Lunges",
            "Forward Lunge",
            "Forward Lunges",
            "Overhead Lunge",
            "Overhead Lunges",
            "DB Walking Lunge",
            "DB Walking Lunges",
            "Dumbbell Walking Lunge",
            "Dumbbell Walking Lunges",
        ),
        aliases=(
            "walking lunge",
            "reverse lunge",
            "forward lunge",
            "overhead lunge",
            "db walking lunge",
        ),
        movement_patterns=(
            MovementPattern.LUNGE,
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
            "Sled Pushes",
            "Sled Pull",
            "Sled Pulls",
        ),
        aliases=(
            "sled push",
            "sled pull",
        ),
        movement_patterns=(
            MovementPattern.LOCOMOTION,
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="devils_press",
        display_name="Devil's Press",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Devil's Press",
            "Devil's Presses",
            "Single DB Devil's Press",
            "Single DB Devil's Presses",
            "Double DB Devil's Press",
            "Double DB Devil's Presses",
            "Single Dumbbell Devil's Press",
            "Single Dumbbell Devil's Presses",
            "Double Dumbbell Devil's Press",
            "Double Dumbbell Devil's Presses",
        ),
        aliases=(
            "devils press",
            "single db devils press",
            "double db devils press",
        ),
        movement_patterns=(
            MovementPattern.HINGE,
            MovementPattern.HORIZONTAL_PUSH,
        ),
        notes="Burpee combined with a dumbbell snatch.",
    )
)

register(
    CrossFitMovement(
        movement_id="man_maker",
        display_name="Man Maker",
        category=MovementCategory.FUNCTIONAL,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Man Maker",
            "Man Makers",
            "Single DB Man Maker",
            "Single DB Man Makers",
            "Double DB Man Maker",
            "Double DB Man Makers",
            "Single Dumbbell Man Maker",
            "Single Dumbbell Man Makers",
            "Double Dumbbell Man Maker",
            "Double Dumbbell Man Makers",
        ),
        aliases=(
            "man maker",
            "man makers",
        ),
        movement_patterns=(
            MovementPattern.HINGE,
            MovementPattern.HORIZONTAL_PUSH,
            MovementPattern.VERTICAL_PUSH,
        ),
        notes="Compound dumbbell movement with push-up, row and press.",
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
            "Wall Push-ups",
            "Incline Push-up",
            "Incline Push-ups",
            "Knee Push-up",
            "Knee Push-ups",
            "Push-up",
            "Push-ups",
            "Hand Release Push-up",
            "Hand Release Push-ups",
            "Deficit Push-up",
            "Deficit Push-ups",
            "Ring Push-up",
            "Ring Push-ups",
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
        movement_patterns=(
            MovementPattern.HORIZONTAL_PUSH,
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
            "Ring Rows",
            "Band Pull-up",
            "Band Pull-ups",
            "Jumping Pull-up",
            "Jumping Pull-ups",
            "Pull-up",
            "Pull-ups",
            "Strict Pull-up",
            "Strict Pull-ups",
            "Kipping Pull-up",
            "Kipping Pull-ups",
        ),
        aliases=(
            "banded pull up",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PULL,
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
            "Chest-to-Bar",
            "Chest-to-Bars",
            "Chest-to-Bar Pull-up",
            "Chest-to-Bar Pull-ups",
            "Strict Chest-to-Bar",
            "Strict Chest-to-Bars",
            "Butterfly Chest-to-Bar",
            "Butterfly Chest-to-Bars",
        ),
        aliases=(
            "ctb",
            "c2b",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PULL,
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
            "Bar Muscle-ups",
            "Strict Bar Muscle-up",
            "Strict Bar Muscle-ups",
            "Ring Muscle-up",
            "Ring Muscle-ups",
            "Strict Ring Muscle-up",
            "Strict Ring Muscle-ups",
        ),
        aliases=(
            "bar muscle up",
            "bar mu",
            "ring muscle up",
            "ring mu",
            "strict bar muscle up",
            "strict ring muscle up",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PULL,
            MovementPattern.VERTICAL_PUSH,
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
            "Wall Handstand Holds",
            "Freestanding Handstand",
            "Freestanding Handstands",
            "Wall Walk",
            "Wall Walks",
        ),
        aliases=(
            "hs hold",
            "hs",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PUSH,
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
            "Box Handstand Push-ups",
            "Strict Handstand Push-up",
            "Strict Handstand Push-ups",
            "Kipping Handstand Push-up",
            "Kipping Handstand Push-ups",
            "Deficit Handstand Push-up",
            "Deficit Handstand Push-ups",
        ),
        aliases=(
            "hspu",
            "strict hspu",
            "kipping hspu",
            "deficit hspu",
            "box hspu",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PUSH,
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
            "Handstand Walks",
        ),
        aliases=(
            "hs walk",
            "hsw",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PUSH,
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
            "Knee Raise",
            "Knee Raises",
            "Hanging Knee Raise",
            "Hanging Knee Raises",
            "Leg Raise",
            "Leg Raises",
            "Hanging Leg Raise",
            "Hanging Leg Raises",
            "Toes-to-Bar",
            "Strict Toes-to-Bar",
            "Toes-to-Bars",
            "Strict Toes-to-Bars",
        ),
        aliases=(
            "ttb",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PULL,
            MovementPattern.CORE_FLEXION,
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
            "Assisted Rope Climbs",
            "Rope Climb",
            "Rope Climbs",
            "Legless Rope Climb",
            "Legless Rope Climbs",
        ),
        aliases=(
            "legless rope climb",
            "assisted rope climb",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PULL,
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
            "Bench Dips",
            "Ring Dip",
            "Ring Dips",
            "Strict Ring Dip",
            "Strict Ring Dips",
        ),
        aliases=(
            "bench dip",
            "strict ring dip",
            "dip",
        ),
        movement_patterns=(
            MovementPattern.VERTICAL_PUSH,
        ),
    )
)

register(
    CrossFitMovement(
        movement_id="pistol",
        display_name="Pistols",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Pistol",
            "Pistols",
            "Assisted Pistol",
            "Assisted Pistols",
            "Pistol Squat",
            "Pistol Squats",
            "Weighted Pistol",
            "Weighted Pistols",
        ),
        aliases=(
            "pistol",
            "pistol squat",
            "single leg squat",
            "weighted pistol",
            "assisted pistol",
        ),
        movement_patterns=(
            MovementPattern.SQUAT,
        ),
        notes="Single-leg squat progression.",
    )
)

register(
    CrossFitMovement(
        movement_id="sit_up",
        display_name="Sit-up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Sit-up",
            "Sit-ups",
            "AbMat Sit-up",
            "AbMat Sit-ups",
            "Anchored Sit-up",
            "Anchored Sit-ups",
            "Butterfly Sit-up",
            "Butterfly Sit-ups",
            "GHD Sit-up",
            "GHD Sit-ups",
        ),
        aliases=(
            "sit up",
            "sit ups",
            "abmat sit up",
            "abmat sit ups",
            "anchored sit up",
            "anchored sit ups",
            "butterfly sit up",
            "butterfly sit ups",
            "ghd sit up",
            "ghd sit ups",
        ),
        movement_patterns=(
            MovementPattern.CORE_FLEXION,
        ),
        notes="Tracks all sit-up variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="russian_twist",
        display_name="Russian Twist",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Russian Twist",
            "Russian Twists",
            "Weighted Russian Twist",
            "Weighted Russian Twists",
        ),
        aliases=(
            "russian twist",
            "russian twists",
            "weighted russian twist",
            "weighted russian twists",
        ),
        movement_patterns=(
            MovementPattern.ROTATION,
        ),
        notes="Tracks all Russian Twist variations.",
    )
)

register(
    CrossFitMovement(
        movement_id="v_up",
        display_name="V-Up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "V-Up",
            "V-Ups",
        ),
        aliases=(
            "v up",
            "v ups",
        ),
        movement_patterns=(
            MovementPattern.CORE_FLEXION,
        ),
        notes="Dynamic core flexion exercise.",
    )
)

register(
    CrossFitMovement(
        movement_id="hollow_rock",
        display_name="Hollow Rock",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.SCALED,
        variants=(
            "Hollow Rock",
            "Hollow Rocks",
        ),
        aliases=(
            "hollow rock",
            "hollow rocks",
        ),
        movement_patterns=(
            MovementPattern.CORE_FLEXION,
        ),
        notes="Dynamic hollow body progression.",
    )
)

register(
    CrossFitMovement(
        movement_id="tuck_up",
        display_name="Tuck-up",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.BEGINNER,
        variants=(
            "Tuck-up",
            "Tuck-ups",
            "Tuck Up",
            "Tuck Ups",
        ),
        aliases=(
            "tuck up",
            "tuck ups",
        ),
        movement_patterns=(
            MovementPattern.CORE_FLEXION,
        ),
        notes="Dynamic core flexion exercise.",
    )
)

register(
    CrossFitMovement(
        movement_id="windshield_wiper",
        display_name="Windshield Wiper",
        category=MovementCategory.GYMNASTICS,
        minimum_level=AthleteLevel.ADVANCED,
        variants=(
            "Windshield Wiper",
            "Windshield Wipers",
            "Hanging Windshield Wiper",
            "Hanging Windshield Wipers",
        ),
        aliases=(
            "windshield wiper",
            "windshield wipers",
            "hanging windshield wiper",
            "hanging windshield wipers",
        ),
        movement_patterns=(
            MovementPattern.ROTATION,
            MovementPattern.CORE_FLEXION,
        ),
        notes="Advanced rotational core exercise.",
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
        movement_patterns=(
            MovementPattern.LOCOMOTION,
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
        movement_patterns=(
            MovementPattern.LOCOMOTION,
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
        movement_patterns=(
            MovementPattern.LOCOMOTION,
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
        movement_patterns=(
            MovementPattern.LOCOMOTION,
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
        movement_patterns=(
            MovementPattern.LOCOMOTION,
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