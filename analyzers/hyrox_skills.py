"""HYROX skill analysis with exact, close-variant and transfer exposure."""
from __future__ import annotations

from collections import defaultdict
from models.parsed_workout import ParsedWorkout
from services.movement_registry import find_movement, normalize_name

HYROX_SKILLS = (
    "running", "ski_erg", "sled_push", "sled_pull", "burpee_broad_jump",
    "row", "farmers_carry", "sandbag_lunge", "wall_ball",
)

# Raw-name overrides preserve specificity that would be lost after movement-family lookup.
RAW_RELATIONS = {
    "sled push": ("sled_push", "exact"),
    "sled pushes": ("sled_push", "exact"),
    "prowler push": ("sled_push", "close_variant"),
    "sled pull": ("sled_pull", "exact"),
    "sled pulls": ("sled_pull", "exact"),
    "rope sled pull": ("sled_pull", "exact"),
    "backward sled drag": ("sled_pull", "close_variant"),
    "burpee broad jump": ("burpee_broad_jump", "exact"),
    "burpee broad jumps": ("burpee_broad_jump", "exact"),
    "bbj": ("burpee_broad_jump", "exact"),
    "sandbag lunge": ("sandbag_lunge", "exact"),
    "sandbag lunges": ("sandbag_lunge", "exact"),
    "sandbag walking lunge": ("sandbag_lunge", "exact"),
    "sandbag walking lunges": ("sandbag_lunge", "exact"),
    "weighted walking lunge": ("sandbag_lunge", "close_variant"),
    "weighted walking lunges": ("sandbag_lunge", "close_variant"),
    "db walking lunge": ("sandbag_lunge", "close_variant"),
    "db walking lunges": ("sandbag_lunge", "close_variant"),
    "dumbbell walking lunge": ("sandbag_lunge", "close_variant"),
    "dumbbell walking lunges": ("sandbag_lunge", "close_variant"),
    "walking lunge": ("sandbag_lunge", "transfer"),
    "walking lunges": ("sandbag_lunge", "transfer"),
    "farmer carry": ("farmers_carry", "exact"),
    "farmers carry": ("farmers_carry", "exact"),
    "farmer carries": ("farmers_carry", "exact"),
    "kb farmers carry": ("farmers_carry", "exact"),
    "kettlebell farmers carry": ("farmers_carry", "exact"),
    "suitcase carry": ("farmers_carry", "transfer"),
}

RANK = {"transfer": 1, "close_variant": 2, "exact": 3}


def _relation_for(raw_name: str, canonical_name: str):
    raw = normalize_name(raw_name or "")
    if raw in RAW_RELATIONS:
        return RAW_RELATIONS[raw]
    movement = find_movement(raw_name or "") or find_movement(canonical_name or "")
    if movement is None or not movement.hyrox_relations:
        return None
    # Families with two exact HYROX stations (sled) require raw specificity.
    if movement.movement_id == "sled":
        return None
    return movement.hyrox_relations[0]


def analyze_hyrox_skills(parsed_workout: ParsedWorkout) -> dict[str, dict]:
    result = defaultdict(lambda: {"exact": 0, "close_variant": 0, "transfer": 0, "best_match": None})
    for segment in parsed_workout.segments:
        for element in segment.elements:
            relation = _relation_for(element.movement.raw_name, element.movement.canonical_name)
            if relation is None:
                continue
            skill, specificity = relation
            result[skill][specificity] += 1
            current = result[skill]["best_match"]
            if current is None or RANK[specificity] > RANK[current]:
                result[skill]["best_match"] = specificity
    return dict(result)
