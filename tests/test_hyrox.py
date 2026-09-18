from analyzers.hyrox_skills import analyze_hyrox_skills
from models.parsed_workout import ParsedWorkout, WorkoutSegment, WorkoutElement, Movement
from services.hyrox import get_race_loads


def _workout(*names: str) -> ParsedWorkout:
    return ParsedWorkout(segments=[WorkoutSegment(name="test", elements=[WorkoutElement(movement=Movement(raw_name=n, canonical_name=n)) for n in names])])


def test_hyrox_exact_and_transfer():
    result = analyze_hyrox_skills(_workout("Wall Balls", "Thrusters", "Weighted Walking Lunges", "Sandbag Lunges"))
    assert result["wall_ball"]["exact"] == 1
    assert result["wall_ball"]["transfer"] == 1
    assert result["sandbag_lunge"]["close_variant"] == 1
    assert result["sandbag_lunge"]["exact"] == 1


def test_sled_push_pull_stay_separate():
    result = analyze_hyrox_skills(_workout("Sled Push", "Sled Pull"))
    assert result["sled_push"]["exact"] == 1
    assert result["sled_pull"]["exact"] == 1


def test_race_loads():
    assert get_race_loads(category="Women", division="Open", race_format="Singles")["wall_ball_kg"] == 4
    assert get_race_loads(category="Mixed", division="Open", race_format="Doubles")["sled_push_kg"] == 152
