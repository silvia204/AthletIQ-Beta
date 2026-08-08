from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ==========================================================
# Movement
# ==========================================================

@dataclass(slots=True)
class Movement:
    """
    Eine erkannte Bewegung.

    raw_name: Originalbezeichnung aus dem Workout.

    canonical_name: Eindeutiger interner Name.
    """

    raw_name: str

    canonical_name: str

    equipment: str | None = None


# ==========================================================
# Intensitätsvorgaben
# ==========================================================

@dataclass(slots=True)
class IntensityPrescription:
    """
    Beschreibt die vorgegebene Intensität.

    Beispiele:
    - 100 kg
    - 80 %1RM
    - RPE 8
    - RIR 2
    - Tempo 31X1
    """

    weight: float | None = None

    weight_unit: str | None = None

    percent_1rm: float | None = None

    prescribed_rpe: float | None = None

    rir: int | None = None

    tempo: str | None = None


# ==========================================================
# Workout Element
# ==========================================================

@dataclass(slots=True)
class WorkoutElement:
    """
    Kleinste beschreibbare Trainingseinheit.

    Beispiele:

    - 10 Burpees
    - 400 m Run
    - 5 Pull-ups
    - 5x5 Back Squat
    """

    movement: Movement

    reps: int | None = None

    sets: int | None = None

    intensity: IntensityPrescription = field(
        default_factory=IntensityPrescription
    )

    distance: float | None = None

    distance_unit: str | None = None

    duration: float | None = None

    duration_unit: str | None = None

    calories: int | None = None

    notes: str | None = None


# ==========================================================
# Workout Segment
# ==========================================================

@dataclass(slots=True)
class WorkoutSegment:
    """
    Ein logisch zusammengehöriger Trainingsblock.

    Beispiele:

    - Warm-up
    - Strength
    - Skill
    - Conditioning
    - Cool-down
    """

    type: str = "unknown"

    name: str | None = None

    rounds: int | None = None

    time_cap_minutes: int | None = None

    elements: list[WorkoutElement] = field(
        default_factory=list
    )

    notes: str | None = None


# ==========================================================
# Parsed Workout
# ==========================================================

@dataclass(slots=True)
class ParsedWorkout:
    """
    Sportartenneutrale Beschreibung eines Workouts.

    Enthält ausschließlich Rohdaten.

    Keine Analyse.
    Keine Klassifikation.
    Keine Interpretation.
    """

    segments: list[WorkoutSegment] = field(
        default_factory=list
    )

    notes: str | None = None

    def to_dict(self) -> dict:
        """
        Serialisiert das ParsedWorkout rekursiv
        als Dictionary.
        """
        return asdict(self)