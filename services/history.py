from typing import Any

import pandas as pd

from services.sheets import read_workout_history
from services.utils import (
    json_loads_from_sheet,
    safely_convert_to_int,
)

from services.movement_mapper import movement_ids
from services.athlete_level import expected_ids
from services.movement_registry import AthleteLevel


DIMENSION_COLUMNS = {
    "movement_pattern_load": "bewegungsmuster_json",
    "muscle_group_load": "muskelgruppen_json",
    "training_goal_counts": "trainingsziele_json",
    "load_type_load": "belastungsarten_json",
    "volume_totals": "trainingsvolumen_json",
}


def classify_training_content(
    workout_text: str,
) -> set[str]:
    """
    Legacy-Fallback für alte Workouts ohne gespeicherte
    Trainingsklassifikation.

    Neue Workouts werden bevorzugt über die JSON-Spalten
    ausgewertet.
    """

    text = str(workout_text).casefold()
    categories: set[str] = set()

    if any(
        term in text
        for term in [
            "run",
            "laufen",
            "running",
            "jog",
            "tempo run",
            "laufinterval",
        ]
    ):
        categories.add("Laufen")

    if any(
        term in text
        for term in [
            "rowing",
            "row erg",
            "concept2 row",
            "bike",
            "echo bike",
            "assault bike",
            "ski erg",
            "skierg",
        ]
    ):
        categories.add("Cardio-Ergometer")

    if any(
        term in text
        for term in [
            "deadlift",
            "kreuzheben",
            "rdl",
            "romanian deadlift",
            "good morning",
            "kettlebell swing",
        ]
    ):
        categories.add("Hintere Kette / Hinge")

    if any(
        term in text
        for term in [
            "squat",
            "kniebeuge",
            "thruster",
            "wall ball",
            "lunge",
            "ausfallschritt",
            "step-up",
        ]
    ):
        categories.add("Knie-dominant / Beine")

    if any(
        term in text
        for term in [
            "bench press",
            "bankdrücken",
            "push-up",
            "push up",
            "shoulder press",
            "strict press",
            "push press",
            "jerk",
            "dip",
        ]
    ):
        categories.add("Drücken / Push")

    if any(
        term in text
        for term in [
            "pull-up",
            "pullup",
            "klimmzug",
            "ring row",
            "bent over row",
            "barbell row",
            "dumbbell row",
            "lat pull",
            "muscle-up",
        ]
    ):
        categories.add("Ziehen / Pull")

    if any(
        term in text
        for term in [
            "plank",
            "sit-up",
            "situp",
            "toes to bar",
            "core",
            "hollow",
            "v-up",
            "dead bug",
        ]
    ):
        categories.add("Core")

    if any(
        term in text
        for term in [
            "clean",
            "snatch",
            "jerk",
            "olympic lifting",
            "reißen",
            "umsetzen",
            "stoßen",
        ]
    ):
        categories.add(
            "Olympisches Gewichtheben"
        )

    if any(
        term in text
        for term in [
            "amrap",
            "emom",
            "rft",
            "for time",
            "metcon",
            "chipper",
        ]
    ):
        categories.add(
            "Metcon / hohe Intensität"
        )

    if any(
        term in text
        for term in [
            "mobility",
            "mobilität",
            "stretch",
            "recovery",
            "easy run",
            "locker",
            "zone 2",
            "zone2",
        ]
    ):
        categories.add(
            "Regeneration / niedrige Intensität"
        )

    if any(
        term in text
        for term in [
            "sled push",
            "sled pull",
            "farmers carry",
            "farmer carry",
            "sandbag",
        ]
    ):
        categories.add(
            "Hyrox / funktioneller Transport"
        )

    return categories


def get_user_training_history(
    *,
    conn: Any,
    spreadsheet_url: str,
    worksheet_name: str,
    columns: list[str],
    athlete_name: str,
    days: int = 28,
) -> pd.DataFrame:
    """
    Lädt die Historie eines Athleten für einen bestimmten
    Zeitraum.
    """

    if conn is None or not athlete_name.strip():
        return pd.DataFrame(columns=columns)

    history = read_workout_history(
        conn=conn,
        spreadsheet_url=spreadsheet_url,
        worksheet_name=worksheet_name,
        columns=columns,
    )

    if history.empty:
        return pd.DataFrame(columns=columns)

    normalized_names = (
        history["name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    athlete_history = history[
        normalized_names
        == athlete_name.strip().casefold()
    ].copy()

    if athlete_history.empty:
        return pd.DataFrame(columns=columns)

    athlete_history[
        "zeitstempel_parsed"
    ] = pd.to_datetime(
        athlete_history["zeitstempel"],
        errors="coerce",
        utc=True,
    )

    cutoff = (
        pd.Timestamp.now(tz="UTC")
        - pd.Timedelta(days=days)
    )

    athlete_history = athlete_history[
        athlete_history[
            "zeitstempel_parsed"
        ].notna()
        & (
            athlete_history[
                "zeitstempel_parsed"
            ]
            >= cutoff
        )
    ].copy()

    athlete_history["rpe_numeric"] = (
        pd.to_numeric(
            athlete_history["rpe"],
            errors="coerce",
        )
    )

    athlete_history["score_numeric"] = (
        pd.to_numeric(
            athlete_history["score"],
            errors="coerce",
        )
    )

    athlete_history["dauer_numeric"] = (
        pd.to_numeric(
            athlete_history["dauer_minuten"],
            errors="coerce",
        )
    )

    return athlete_history.sort_values(
        "zeitstempel_parsed",
        ascending=True,
    )


def normalize_dimension_key(
    key: Any,
) -> str:
    """
    Normalisiert Klassifikations-Keys aus KI- und Sheet-Daten.

    Beispiele:
    - "Horizontal Push" -> "horizontal_push"
    - "horizontal-push" -> "horizontal_push"
    - "  HINGE  " -> "hinge"
    """

    normalized = (
        str(key)
        .strip()
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )

    while "__" in normalized:
        normalized = normalized.replace(
            "__",
            "_",
        )

    return normalized.strip("_")


def merge_numeric_dict(
    target: dict[str, float],
    source: dict[str, Any],
) -> None:
    """
    Addiert numerische Werte eines Dictionaries zum Ziel.
    """

    if not isinstance(source, dict):
        return

    for key, value in source.items():
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue

        normalized_key = (
            normalize_dimension_key(key)
        )

        if not normalized_key:
            continue

        target[normalized_key] = round(
            target.get(
                normalized_key,
                0.0,
            )
            + numeric_value,
            3,
        )


def aggregate_training_dimensions(
    history: pd.DataFrame,
) -> dict[str, dict[str, float]]:
    """
    Aggregiert alle gespeicherten Trainingsdimensionen.
    """

    result = {
        "movement_pattern_load": {},
        "muscle_group_load": {},
        "training_goal_counts": {},
        "load_type_load": {},
        "volume_totals": {},
    }

    if history.empty:
        return result

    for _, row in history.iterrows():
        for result_key, column_name in (
            DIMENSION_COLUMNS.items()
        ):
            raw_value = row.get(
                column_name,
                "",
            )

            parsed_value = json_loads_from_sheet(
                raw_value,
                default={},
            )

            merge_numeric_dict(
                result[result_key],
                parsed_value,
            )

    return result


def calculate_load_statistics(
    history: pd.DataFrame,
) -> dict[str, Any]:
    """
    Berechnet Belastungskennzahlen eines Zeitfensters.
    """

    if history.empty:
        return {
            "sessions": 0,
            "minutes": 0,
            "average_rpe": None,
            "average_score": None,
            "total_score": 0.0,
            "high_rpe_sessions": 0,
            "very_high_rpe_sessions": 0,
            "low_rpe_sessions": 0,
        }

    rpe_values = pd.to_numeric(
        history["rpe_numeric"],
        errors="coerce",
    )

    score_values = pd.to_numeric(
        history["score_numeric"],
        errors="coerce",
    )

    duration_values = pd.to_numeric(
        history["dauer_numeric"],
        errors="coerce",
    )

    return {
        "sessions": int(len(history)),
        "minutes": int(
            duration_values.fillna(0).sum()
        ),
        "average_rpe": (
            round(
                float(
                    rpe_values.dropna().mean()
                ),
                1,
            )
            if not rpe_values.dropna().empty
            else None
        ),
        "average_score": (
            round(
                float(
                    score_values.dropna().mean()
                ),
                1,
            )
            if not score_values.dropna().empty
            else None
        ),
        "total_score": round(
            float(
                score_values.fillna(0).sum()
            ),
            1,
        ),
        "high_rpe_sessions": int(
            (rpe_values >= 8).sum()
        ),
        "very_high_rpe_sessions": int(
            (rpe_values >= 9).sum()
        ),
        "low_rpe_sessions": int(
            (rpe_values <= 5).sum()
        ),
    }


def filter_history_window(
    history: pd.DataFrame,
    *,
    days: int,
) -> pd.DataFrame:
    """
    Schneidet die Historie auf die letzten X Tage zu.
    """

    if history.empty:
        return history.copy()

    cutoff = (
        pd.Timestamp.now(tz="UTC")
        - pd.Timedelta(days=days)
    )

    return history[
        history["zeitstempel_parsed"]
        >= cutoff
    ].copy()


def build_window_summary(
    history: pd.DataFrame,
    *,
    days: int,
) -> dict[str, Any]:
    """
    Erstellt Kennzahlen und Trainingsdimensionen für
    ein einzelnes Zeitfenster.
    """

    window_history = filter_history_window(
        history,
        days=days,
    )

    dimensions = (
        aggregate_training_dimensions(
            window_history
        )
    )

    statistics = (
        calculate_load_statistics(
            window_history
        )
    )

    return {
        "days": days,
        **statistics,
        **dimensions,
    }


def build_history_windows(
    history: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """
    Erstellt mehrere Zeitfenster für Trendanalysen.
    """

    return {
        "7_days": build_window_summary(
            history,
            days=7,
        ),
        "14_days": build_window_summary(
            history,
            days=14,
        ),
        "28_days": build_window_summary(
            history,
            days=28,
        ),
        "90_days": build_window_summary(
            history,
            days=90,
        ),
    }


def calculate_days_since_last_load(
    history: pd.DataFrame,
) -> dict[str, dict[str, int]]:
    """
    Berechnet für jede Dimension, wie viele Tage seit der
    letzten positiven Belastung vergangen sind.
    """

    result: dict[str, dict[str, int]] = {
        "movement_patterns": {},
        "muscle_groups": {},
        "training_goals": {},
        "load_types": {},
    }

    if history.empty:
        return result

    column_mapping = {
        "movement_patterns": (
            "bewegungsmuster_json"
        ),
        "muscle_groups": (
            "muskelgruppen_json"
        ),
        "training_goals": (
            "trainingsziele_json"
        ),
        "load_types": (
            "belastungsarten_json"
        ),
    }

    now = pd.Timestamp.now(tz="UTC")

    sorted_history = history.sort_values(
        "zeitstempel_parsed",
        ascending=False,
    )

    for result_key, column_name in (
        column_mapping.items()
    ):
        latest_dates: dict[
            str,
            pd.Timestamp,
        ] = {}

        for _, row in (
            sorted_history.iterrows()
        ):
            timestamp = row.get(
                "zeitstempel_parsed"
            )

            if pd.isna(timestamp):
                continue

            values = json_loads_from_sheet(
                row.get(column_name, ""),
                default={},
            )

            if not isinstance(values, dict):
                continue

            for category, raw_value in (
                values.items()
            ):
                try:
                    numeric_value = float(
                        raw_value
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if numeric_value <= 0:
                    continue

                category_name = (
                    normalize_dimension_key(
                        category
                    )
                )

                if not category_name:
                    continue

                if category_name not in latest_dates:
                    latest_dates[
                        category_name
                    ] = timestamp

        for category, timestamp in (
            latest_dates.items()
        ):
            result[result_key][
                category
            ] = max(
                0,
                int(
                    (
                        now
                        - timestamp
                    ).total_seconds()
                    // 86400
                ),
            )

    return result


def calculate_load_change(
    current_load: float,
    previous_load: float,
) -> float | None:
    """
    Berechnet die prozentuale Veränderung zweier Lasten.
    """

    if previous_load <= 0:
        return None

    return round(
        (
            current_load
            - previous_load
        )
        / previous_load
        * 100,
        1,
    )


def build_overload_signals(
    *,
    history: pd.DataFrame,
    windows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Erkennt Warnsignale für hohe oder schnell steigende
    Belastung.

    Diese Signale sind keine medizinische Diagnose.
    """

    signals: list[dict[str, Any]] = []

    last_7 = windows["7_days"]

    now = pd.Timestamp.now(tz="UTC")
    previous_cutoff = (
        now - pd.Timedelta(days=14)
    )
    current_cutoff = (
        now - pd.Timedelta(days=7)
    )

    previous_7_history = history[
        (
            history["zeitstempel_parsed"]
            >= previous_cutoff
        )
        & (
            history["zeitstempel_parsed"]
            < current_cutoff
        )
    ].copy()

    previous_7_stats = (
        calculate_load_statistics(
            previous_7_history
        )
    )

    load_change = calculate_load_change(
        float(last_7["total_score"]),
        float(
            previous_7_stats[
                "total_score"
            ]
        ),
    )

    if (
        load_change is not None
        and load_change >= 50
        and last_7["sessions"] >= 3
    ):
        signals.append(
            {
                "code": (
                    "rapid_weekly_load_increase"
                ),
                "severity": "warning",
                "message": (
                    "Die Belastung der letzten "
                    f"7 Tage liegt {load_change:.1f} % "
                    "über den vorherigen 7 Tagen."
                ),
            }
        )

    if last_7["high_rpe_sessions"] >= 3:
        signals.append(
            {
                "code": (
                    "repeated_high_rpe"
                ),
                "severity": "warning",
                "message": (
                    "In den letzten 7 Tagen gab es "
                    f"{last_7['high_rpe_sessions']} "
                    "Einheiten mit RPE 8 oder höher."
                ),
            }
        )

    if (
        last_7["very_high_rpe_sessions"]
        >= 2
    ):
        signals.append(
            {
                "code": (
                    "repeated_very_high_rpe"
                ),
                "severity": "warning",
                "message": (
                    "Mehrere Einheiten mit RPE 9 "
                    "oder höher lagen innerhalb "
                    "der letzten 7 Tage."
                ),
            }
        )

    if (
        last_7["sessions"] >= 5
        and last_7["low_rpe_sessions"] == 0
    ):
        signals.append(
            {
                "code": (
                    "insufficient_easy_sessions"
                ),
                "severity": "notice",
                "message": (
                    "Bei mindestens fünf Einheiten "
                    "in sieben Tagen wurde keine "
                    "leichte Einheit mit RPE 5 oder "
                    "niedriger dokumentiert."
                ),
            }
        )

    load_types = last_7.get(
        "load_type_load",
        {},
    )

    for load_type in [
        "mechanical",
        "eccentric",
        "impact",
        "neuromuscular",
    ]:
        value = float(
            load_types.get(
                load_type,
                0.0,
            )
        )

        if value >= 3.5:
            signals.append(
                {
                    "code": (
                        f"high_{load_type}_load"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Die Belastungsart "
                        f"„{load_type}“ war in den "
                        "letzten 7 Tagen mehrfach "
                        "deutlich vertreten."
                    ),
                }
            )

    muscle_load = last_7.get(
        "muscle_group_load",
        {},
    )

    for muscle, value in (
        muscle_load.items()
    ):
        if float(value) >= 4.0:
            signals.append(
                {
                    "code": (
                        f"high_recent_{muscle}_load"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Die Muskelgruppe "
                        f"„{muscle}“ wurde in den "
                        "letzten 7 Tagen wiederholt "
                        "stark belastet."
                    ),
                }
            )

    return signals


def build_undertraining_signals(
    *,
    windows: dict[str, dict[str, Any]],
    days_since_last_load: dict[
        str,
        dict[str, int],
    ],
) -> list[dict[str, Any]]:
    """
    Erkennt länger fehlende oder deutlich
    unterrepräsentierte Trainingsanteile.
    """

    signals: list[dict[str, Any]] = []

    last_28 = windows["28_days"]

    movement_load = last_28.get(
        "movement_pattern_load",
        {},
    )

    muscle_load = last_28.get(
        "muscle_group_load",
        {},
    )

    goal_counts = last_28.get(
        "training_goal_counts",
        {},
    )

    movement_days = (
        days_since_last_load.get(
            "movement_patterns",
            {},
        )
    )

    muscle_days = (
        days_since_last_load.get(
            "muscle_groups",
            {},
        )
    )

    goal_days = (
        days_since_last_load.get(
            "training_goals",
            {},
        )
    )

    important_movements = [
        "squat",
        "hinge",
        "horizontal_push",
        "vertical_push",
        "horizontal_pull",
        "vertical_pull",
        "carry",
        "anti_rotation",
        "anti_extension",
    ]

    for movement in important_movements:
        load_value = float(
            movement_load.get(
                movement,
                0.0,
            )
        )

        days_since = movement_days.get(
            movement
        )

        if (
            load_value == 0
            and last_28["sessions"] >= 4
        ):
            signals.append(
                {
                    "code": (
                        f"missing_{movement}"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Das Bewegungsmuster "
                        f"„{movement}“ wurde in den "
                        "letzten 28 Tagen nicht "
                        "dokumentiert."
                    ),
                }
            )

        elif (
            days_since is not None
            and days_since >= 14
        ):
            signals.append(
                {
                    "code": (
                        f"{movement}_not_recent"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Das Bewegungsmuster "
                        f"„{movement}“ wurde seit "
                        f"{days_since} Tagen nicht "
                        "mehr belastet."
                    ),
                }
            )

    ratio_pairs = [
        (
            "quadriceps",
            "hamstrings",
            "quadriceps_to_hamstrings",
        ),
        (
            "chest",
            "latissimus",
            "chest_to_latissimus",
        ),
        (
            "front_delts",
            "rear_delts",
            "front_to_rear_delts",
        ),
    ]

    for dominant, counterpart, code in (
        ratio_pairs
    ):
        dominant_value = float(
            muscle_load.get(
                dominant,
                0.0,
            )
        )

        counterpart_value = float(
            muscle_load.get(
                counterpart,
                0.0,
            )
        )

        if (
            dominant_value >= 2.0
            and counterpart_value > 0
            and dominant_value
            >= counterpart_value * 2.5
        ):
            signals.append(
                {
                    "code": code,
                    "severity": "notice",
                    "message": (
                        f"„{dominant}“ ist über "
                        "28 Tage deutlich stärker "
                        f"vertreten als "
                        f"„{counterpart}“."
                    ),
                }
            )

    important_muscles = [
        "hamstrings",
        "glutes",
        "latissimus",
        "rear_delts",
        "deep_core",
    ]

    for muscle in important_muscles:
        days_since = muscle_days.get(
            muscle
        )

        if (
            days_since is not None
            and days_since >= 14
        ):
            signals.append(
                {
                    "code": (
                        f"{muscle}_not_recent"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Die Muskelgruppe "
                        f"„{muscle}“ wurde seit "
                        f"{days_since} Tagen nicht "
                        "mehr relevant belastet."
                    ),
                }
            )

    important_goals = [
        "max_strength",
        "aerobic_base",
        "threshold",
        "vo2max",
        "technique",
        "mobility",
        "recovery",
    ]

    for goal in important_goals:
        count = int(
            goal_counts.get(
                goal,
                0,
            )
        )

        days_since = goal_days.get(
            goal
        )

        if (
            count == 0
            and last_28["sessions"] >= 6
        ):
            signals.append(
                {
                    "code": (
                        f"missing_goal_{goal}"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Das Trainingsziel "
                        f"„{goal}“ wurde in den "
                        "letzten 28 Tagen nicht "
                        "dokumentiert."
                    ),
                }
            )

        elif (
            days_since is not None
            and days_since >= 21
        ):
            signals.append(
                {
                    "code": (
                        f"goal_{goal}_not_recent"
                    ),
                    "severity": "notice",
                    "message": (
                        f"Das Trainingsziel "
                        f"„{goal}“ wurde seit "
                        f"{days_since} Tagen nicht "
                        "mehr dokumentiert."
                    ),
                }
            )

    return signals


def build_recent_sessions(
    history: pd.DataFrame,
) -> list[dict[str, Any]]:
    """
    Erstellt eine kompakte Liste der letzten Einheiten.
    """

    sessions: list[dict[str, Any]] = []

    for _, row in history.iterrows():
        timestamp = row.get(
            "zeitstempel_parsed"
        )

        if pd.notna(timestamp):
            displayed_date = (
                timestamp.strftime(
                    "%Y-%m-%d"
                )
            )
        else:
            displayed_date = "Unbekannt"

        legacy_categories = (
            classify_training_content(
                row.get("workout", "")
            )
        )

        sessions.append(
            {
                "zeitstempel": displayed_date,
                "sportart": str(
                    row.get(
                        "sportart",
                        "",
                    )
                ).strip(),
                "dauer_minuten": (
                    safely_convert_to_int(
                        row.get(
                            "dauer_numeric"
                        ),
                        default=0,
                    )
                ),
                "rpe": safely_convert_to_int(
                    row.get(
                        "rpe_numeric"
                    ),
                    default=0,
                ),
                "score": safely_convert_to_int(
                    row.get(
                        "score_numeric"
                    ),
                    default=0,
                ),
                "kategorien": sorted(
                    legacy_categories
                ),
                "bewegungsmuster": (
                    json_loads_from_sheet(
                        row.get(
                            "bewegungsmuster_json",
                            "",
                        ),
                        default={},
                    )
                ),
                "muskelgruppen": (
                    json_loads_from_sheet(
                        row.get(
                            "muskelgruppen_json",
                            "",
                        ),
                        default={},
                    )
                ),
                "trainingsziele": (
                    json_loads_from_sheet(
                        row.get(
                            "trainingsziele_json",
                            "",
                        ),
                        default={},
                    )
                ),
                "belastungsarten": (
                    json_loads_from_sheet(
                        row.get(
                            "belastungsarten_json",
                            "",
                        ),
                        default={},
                    )
                ),
                "verletzungen": str(
                    row.get(
                        "verletzungen",
                        "",
                    )
                ).strip(),
                "kommentar": str(
                    row.get(
                        "kommentar",
                        "",
                    )
                ).strip(),
                "workout": str(
                    row.get(
                        "workout",
                        "",
                    )
                ).strip()[:600],
            }
        )

    return sessions[-12:]


def build_legacy_category_counts(
    history: pd.DataFrame,
) -> dict[str, int]:
    """
    Behält die bisherige Keyword-Auswertung für alte
    Workouts und die bestehende App-Anzeige bei.
    """

    category_counts: dict[str, int] = {}

    for _, row in history.iterrows():
        categories = classify_training_content(
            row.get("workout", "")
        )

        for category in categories:
            category_counts[category] = (
                category_counts.get(
                    category,
                    0,
                )
                + 1
            )

    return category_counts

def build_crossfit_movement_summary(
    history: pd.DataFrame,
    *,
    athlete_level: str = "scaled",
) -> dict[str, Any]:
    """
    Erstellt eine Übersicht der trainierten CrossFit-Movements
    aus den gespeicherten Analyseergebnissen.

    Grundlage ist ausschließlich crossfit_movements_json.
    Historische Workout-Texte werden nicht erneut geparst.
    """

    level_lookup = {
        "beginner": AthleteLevel.BEGINNER,
        "scaled": AthleteLevel.SCALED,
        "advanced": AthleteLevel.ADVANCED,
    }

    level = level_lookup.get(
        str(athlete_level).casefold(),
        AthleteLevel.SCALED,
    )

    expected = expected_ids(level)

    movement_counter: dict[str, int] = {}

    if (
        not history.empty
        and "crossfit_movements_json"
        in history.columns
    ):
        for _, row in history.iterrows():

            movement_data = (
                json_loads_from_sheet(
                    row.get(
                        "crossfit_movements_json",
                        "",
                    ),
                    default={},
                )
            )

            if not isinstance(
                movement_data,
                dict,
            ):
                continue

            for movement_id, raw_count in (
                movement_data.items()
            ):
                movement_id = str(
                    movement_id
                ).strip()

                if not movement_id:
                    continue

                try:
                    count = int(
                        raw_count
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if count <= 0:
                    continue

                movement_counter[
                    movement_id
                ] = (
                    movement_counter.get(
                        movement_id,
                        0,
                    )
                    + count
                )

    completed = set(
        movement_counter.keys()
    )

    covered_movements = (
        completed & expected
    )

    missing = sorted(
        expected - completed
    )

    coverage = (
        round(
            len(covered_movements)
            / len(expected)
            * 100,
            1,
        )
        if expected
        else 100.0
    )

    return {
        "athlete_level": level.value,
        "movements": movement_counter,
        "completed": sorted(
            completed
        ),
        "missing": missing,
        "covered": len(
            covered_movements
        ),
        "expected": len(
            expected
        ),
        "coverage_percent": coverage,
    }

def build_history_summary(
    history: pd.DataFrame,
    *,
    period_days: int = 28,
) -> dict[str, Any]:
    """
    Erstellt die vollständige Trainingshistorienanalyse.

    Enthalten sind:
    - bisherige Kennzahlen,
    - mehrere Zeitfenster,
    - strukturierte Trainingsdimensionen,
    - Tage seit letzter Belastung,
    - Überlastungswarnsignale,
    - Untertrainingssignale.
    """

    if history.empty:
        return {
            "zeitraum_tage": period_days,
            "anzahl_einheiten": 0,
            "einheiten_letzte_7_tage": 0,
            "hinweis": (
                "Keine verwertbare "
                "Trainingshistorie vorhanden."
            ),
            "trainingskategorien": {},
            "gemeldete_beschwerden": [],
            "letzte_einheiten": [],
            "windows": {
                "7_days": {},
                "14_days": {},
                "28_days": {},
                "90_days": {},
            },
            "days_since_last_load": {
                "movement_patterns": {},
                "muscle_groups": {},
                "training_goals": {},
                "load_types": {},
            },
            "overload_signals": [],
            "undertraining_signals": [],
        }

    analysis_history = (
        filter_history_window(
            history,
            days=period_days,
        )
    )

    windows = build_history_windows(
        history
    )

    days_since_last_load = (
        calculate_days_since_last_load(
            history
        )
    )

    overload_signals = (
        build_overload_signals(
            history=history,
            windows=windows,
        )
    )

    undertraining_signals = (
        build_undertraining_signals(
            windows=windows,
            days_since_last_load=(
                days_since_last_load
            ),
        )
    )

    legacy_category_counts = (
        build_legacy_category_counts(
            history
        )
    )

    crossfit_summary = (
    build_crossfit_movement_summary(
        history
    )
)

    injury_entries = (
        analysis_history["verletzungen"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    injury_entries = injury_entries[
        injury_entries != ""
    ].tolist()

    last_7 = windows["7_days"]

    now = pd.Timestamp.now(tz="UTC")

    previous_7_history = history[
        (
            history["zeitstempel_parsed"]
            >= (
                now
                - pd.Timedelta(days=14)
            )
        )
        & (
            history["zeitstempel_parsed"]
            < (
                now
                - pd.Timedelta(days=7)
            )
        )
    ].copy()

    previous_7_stats = (
        calculate_load_statistics(
            previous_7_history
        )
    )

    load_change = calculate_load_change(
        float(last_7["total_score"]),
        float(
            previous_7_stats[
                "total_score"
            ]
        ),
    )

    return {
        "zeitraum_tage": period_days,
        "anzahl_einheiten": int(
            len(analysis_history)
        ),
        "einheiten_letzte_7_tage": int(
            last_7["sessions"]
        ),
        "durchschnittliche_rpe": (
            windows["28_days"][
                "average_rpe"
            ]
        ),
        "durchschnittlicher_score": (
            windows["28_days"][
                "average_score"
            ]
        ),
        "gesamtdauer_minuten": int(
            windows["28_days"][
                "minutes"
            ]
        ),
        "einheiten_mit_rpe_ab_8": int(
            windows["28_days"][
                "high_rpe_sessions"
            ]
        ),
        "einheiten_mit_rpe_ab_9": int(
            windows["28_days"][
                "very_high_rpe_sessions"
            ]
        ),
        "belastung_letzte_7_tage": (
            float(
                last_7["total_score"]
            )
        ),
        "belastung_vorherige_7_tage": (
            float(
                previous_7_stats[
                    "total_score"
                ]
            )
        ),
        "belastungsveraenderung_prozent": (
            load_change
        ),
        "trainingskategorien": (
            legacy_category_counts
        ),
        "crossfit_movements": (
            crossfit_summary["movements"]
        ),

        "crossfit_coverage": {
            "athlete_level": crossfit_summary["athlete_level"],
            "coverage_percent": crossfit_summary["coverage_percent"],
            "covered": crossfit_summary["covered"],
            "expected": crossfit_summary["expected"],
        },

        "missing_crossfit_movements": (
            crossfit_summary["missing"]
        ),
        "gemeldete_beschwerden": (
            injury_entries[-10:]
        ),
        "letzte_einheiten": (
            build_recent_sessions(
                analysis_history
            )
        ),
        "windows": windows,
        "days_since_last_load": (
            days_since_last_load
        ),
        "overload_signals": (
            overload_signals
        ),
        "undertraining_signals": (
            undertraining_signals
        ),
    }


def remove_current_workout_from_history(
    history: pd.DataFrame,
    *,
    current_workout_text: str,
    current_rpe: int,
) -> pd.DataFrame:
    """
    Entfernt die neueste identische Einheit, falls das
    aktuelle Workout bereits gespeichert wurde.
    """

    if history.empty:
        return history

    workout_matches = (
        history["workout"]
        .fillna("")
        .astype(str)
        .str.strip()
        == current_workout_text.strip()
    )

    rpe_matches = (
        pd.to_numeric(
            history["rpe"],
            errors="coerce",
        )
        == current_rpe
    )

    matching_rows = history[
        workout_matches & rpe_matches
    ]

    if matching_rows.empty:
        return history

    timestamps = matching_rows[
        "zeitstempel_parsed"
    ]

    if timestamps.dropna().empty:
        return history

    latest_matching_index = (
        timestamps.idxmax()
    )

    return history.drop(
        index=latest_matching_index
    )