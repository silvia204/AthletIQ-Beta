from services.coach_logic import build_hyrox_focus
from services.training_balance import evaluate_skill_movements


def test_hyrox_skill_rows_include_all_race_skills():
    rows = evaluate_skill_movements(
        counts_28={"wall_ball": 2},
        counts_14={"wall_ball": 1},
        previous_14={"wall_ball": 1},
        sessions_14=4,
        previous_sessions_14=4,
        dimension="hyrox_skills",
    )
    assert len(rows) == 9
    assert {row["key"] for row in rows} == {
        "running", "ski_erg", "sled_push", "sled_pull", "burpee_broad_jump",
        "row", "farmers_carry", "sandbag_lunge", "wall_ball",
    }


def test_hyrox_focus_uses_hyrox_skill_not_generic_movement_gap():
    rows = evaluate_skill_movements(
        counts_28={"wall_ball": 2},
        counts_14={"wall_ball": 1},
        previous_14={"wall_ball": 1},
        sessions_14=4,
        previous_sessions_14=4,
        dimension="hyrox_skills",
    )
    focus = build_hyrox_focus(training_balance={"hyrox_skills": rows})
    assert focus is not None
    assert focus["mode"] == "hyrox"
    assert "HYROX" in focus["recommendation_reason"]
    assert "Bewegungsanteil" not in focus["text"]
