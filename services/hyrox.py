"""HYROX race profile and official race-load reference data."""
from __future__ import annotations

HYROX_RACE_LOADS = {
    "women_open": {"sled_push_kg": 102, "sled_pull_kg": 78, "farmers_carry_kg_each": 16, "sandbag_lunge_kg": 10, "wall_ball_kg": 4},
    "women_pro": {"sled_push_kg": 152, "sled_pull_kg": 103, "farmers_carry_kg_each": 24, "sandbag_lunge_kg": 20, "wall_ball_kg": 6},
    "men_open": {"sled_push_kg": 152, "sled_pull_kg": 103, "farmers_carry_kg_each": 24, "sandbag_lunge_kg": 20, "wall_ball_kg": 6},
    "men_pro": {"sled_push_kg": 202, "sled_pull_kg": 153, "farmers_carry_kg_each": 32, "sandbag_lunge_kg": 30, "wall_ball_kg": 9},
    "mixed_doubles": {"sled_push_kg": 152, "sled_pull_kg": 103, "farmers_carry_kg_each": 24, "sandbag_lunge_kg": 20, "wall_ball_kg": 6},
}


def race_profile_key(*, category: str, division: str, race_format: str) -> str | None:
    category = (category or "").strip().casefold()
    division = (division or "").strip().casefold()
    race_format = (race_format or "").strip().casefold()
    if race_format == "doubles" and category == "mixed":
        return "mixed_doubles"
    if category in {"women", "men"} and division in {"open", "pro"}:
        return f"{category}_{division}"
    return None


def get_race_loads(*, category: str, division: str, race_format: str) -> dict[str, int] | None:
    key = race_profile_key(category=category, division=division, race_format=race_format)
    return dict(HYROX_RACE_LOADS[key]) if key in HYROX_RACE_LOADS else None
