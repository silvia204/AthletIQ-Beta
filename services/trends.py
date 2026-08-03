from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

import pandas as pd

try:
    from services.utils import json_loads_from_sheet
except ImportError:
    import json

    def json_loads_from_sheet(
        value: Any,
        *,
        default: Any,
    ) -> Any:
        """
        Lokaler Fallback, damit dieses Modul auch unabhängig
        von services.utils getestet werden kann.
        """

        if isinstance(value, (dict, list)):
            return value

        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        try:
            return json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return default


DIMENSION_COLUMNS = {
    "training_goals": "trainingsziele_json",
    "movement_patterns": "bewegungsmuster_json",
    "muscle_groups": "muskelgruppen_json",
    "load_types": "belastungsarten_json",
}


TRAINING_GOAL_LABELS = {
    "max_strength": "Maximalkraft",
    "hypertrophy": "Muskelaufbau",
    "strength_endurance": "Kraftausdauer",
    "speed_strength": "Schnellkraft",
    "explosive_strength": "Explosivkraft",
    "aerobic_base": "aerobe Basis",
    "threshold": "Schwellentraining",
    "vo2max": "VO₂max-Training",
    "anaerobic_capacity": "anaerobes Training",
    "technique": "Techniktraining",
    "mobility": "Mobilität",
    "recovery": "Regeneration",
}


MOVEMENT_PATTERN_LABELS = {
    "squat": "Squat",
    "hinge": "Hinge",
    "lunge": "Lunge",
    "horizontal_push": "horizontales Drücken",
    "vertical_push": "vertikales Drücken",
    "horizontal_pull": "horizontales Ziehen",
    "vertical_pull": "vertikales Ziehen",
    "carry": "Carries",
    "core": "Core",
    "locomotion": "Laufen und Locomotion",
    "rotation": "Rotation",
}


def normalize_key(value: Any) -> str:
    """
    Vereinheitlicht Dimensionsschlüssel aus älteren und
    neueren Klassifikationen.
    """

    text = str(value or "").strip().casefold()

    replacements = {
        "-": "_",
        " ": "_",
        "/": "_",
        "\\": "_",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    while "__" in text:
        text = text.replace("__", "_")

    aliases = {
        "zone_2": "aerobic_base",
        "zone2": "aerobic_base",
        "aerobic": "aerobic_base",
        "aerobe_basis": "aerobic_base",
        "maximalkraft": "max_strength",
        "kraftausdauer": "strength_endurance",
        "schwelle": "threshold",
        "mobilitaet": "mobility",
        "mobilität": "mobility",
        "regeneration": "recovery",
        "horizontal_pushes": "horizontal_push",
        "horizontal_pulls": "horizontal_pull",
        "vertical_pushes": "vertical_push",
        "vertical_pulls": "vertical_pull",
        "ziehen": "pull",
        "druecken": "push",
        "drücken": "push",
    }

    return aliases.get(text, text)


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if pd.isna(number):
        return default

    return number


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    return int(round(safe_float(value, float(default))))


def percentage_change(
    current: float,
    previous: float,
) -> float | None:
    """
    Prozentuale Veränderung. None bedeutet, dass kein
    belastbarer Vergleich möglich ist.
    """

    if previous <= 0:
        return None

    return round(
        ((current - previous) / previous) * 100,
        1,
    )


def classify_direction(
    change_percent: float | None,
    *,
    stable_threshold: float = 10.0,
) -> str:
    if change_percent is None:
        return "insufficient_data"

    if change_percent > stable_threshold:
        return "up"

    if change_percent < -stable_threshold:
        return "down"

    return "stable"


def direction_symbol(direction: str) -> str:
    return {
        "up": "↗",
        "down": "↘",
        "stable": "→",
        "insufficient_data": "•",
    }.get(direction, "•")


def prepare_history(
    history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalisiert Zeitstempel und numerische Spalten.
    """

    if history is None or history.empty:
        return pd.DataFrame()

    prepared = history.copy()

    timestamp_column = None

    for candidate in (
        "zeitstempel_parsed",
        "zeitstempel",
        "timestamp",
        "date",
    ):
        if candidate in prepared.columns:
            timestamp_column = candidate
            break

    if timestamp_column is None:
        return pd.DataFrame()

    prepared["_trend_timestamp"] = pd.to_datetime(
        prepared[timestamp_column],
        errors="coerce",
        utc=True,
    )

    prepared = prepared.dropna(
        subset=["_trend_timestamp"]
    )

    numeric_candidates = {
        "_trend_score": (
            "score",
            "load",
            "total_score",
        ),
        "_trend_rpe": (
            "rpe",
            "RPE",
        ),
        "_trend_duration": (
            "dauer_minuten",
            "duration_minutes",
            "duration",
        ),
    }

    for target, candidates in numeric_candidates.items():
        source = next(
            (
                column
                for column in candidates
                if column in prepared.columns
            ),
            None,
        )

        if source is None:
            prepared[target] = 0.0
        else:
            prepared[target] = pd.to_numeric(
                prepared[source],
                errors="coerce",
            ).fillna(0.0)

    return prepared.sort_values(
        "_trend_timestamp"
    )


def filter_period(
    history: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    if history.empty:
        return history.copy()

    return history[
        (history["_trend_timestamp"] >= start)
        & (history["_trend_timestamp"] < end)
    ].copy()


def aggregate_dimension(
    history: pd.DataFrame,
    *,
    column_name: str,
) -> dict[str, float]:
    totals: Counter[str] = Counter()

    if history.empty or column_name not in history.columns:
        return {}

    for raw_value in history[column_name]:
        parsed = json_loads_from_sheet(
            raw_value,
            default={},
        )

        if not isinstance(parsed, dict):
            continue

        for raw_key, raw_amount in parsed.items():
            key = normalize_key(raw_key)
            amount = safe_float(raw_amount)

            if key and amount > 0:
                totals[key] += amount

    return {
        key: round(value, 2)
        for key, value in totals.items()
    }


def period_statistics(
    history: pd.DataFrame,
) -> dict[str, float | int]:
    if history.empty:
        return {
            "sessions": 0,
            "total_load": 0.0,
            "average_rpe": 0.0,
            "minutes": 0.0,
            "training_days": 0,
        }

    valid_rpe = history[
        history["_trend_rpe"] > 0
    ]["_trend_rpe"]

    return {
        "sessions": int(len(history)),
        "total_load": round(
            float(
                history["_trend_score"].sum()
            ),
            1,
        ),
        "average_rpe": round(
            float(valid_rpe.mean())
            if not valid_rpe.empty
            else 0.0,
            1,
        ),
        "minutes": round(
            float(
                history["_trend_duration"].sum()
            ),
            1,
        ),
        "training_days": int(
            history[
                "_trend_timestamp"
            ].dt.date.nunique()
        ),
    }


def describe_load_trend(
    change: float | None,
    direction: str,
) -> str:
    if direction == "insufficient_data":
        return (
            "Noch nicht genügend Daten für einen "
            "Belastungsvergleich"
        )

    if direction == "stable":
        return "Trainingsbelastung bleibt stabil"

    magnitude = abs(change or 0)

    if magnitude >= 50:
        strength = "deutlich"
    elif magnitude >= 25:
        strength = "moderat"
    else:
        strength = "leicht"

    if direction == "up":
        return f"Trainingsbelastung steigt {strength}"

    return f"Trainingsbelastung sinkt {strength}"


def describe_frequency_trend(
    current_sessions: int,
    previous_sessions: int,
) -> tuple[str, float | None, str]:
    change = percentage_change(
        float(current_sessions),
        float(previous_sessions),
    )
    direction = classify_direction(
        change,
        stable_threshold=15,
    )

    if previous_sessions == 0:
        if current_sessions > 0:
            return (
                "up",
                None,
                "Neue Trainingsaktivität in dieser Woche",
            )

        return (
            "insufficient_data",
            None,
            "Noch keine Trainingsfrequenz erkennbar",
        )

    difference = current_sessions - previous_sessions

    if difference >= 2:
        text = "Du trainierst aktuell häufiger"
    elif difference <= -2:
        text = "Du trainierst aktuell seltener"
    else:
        direction = "stable"
        text = "Trainingshäufigkeit bleibt stabil"

    return direction, change, text


def describe_rpe_trend(
    current_rpe: float,
    previous_rpe: float,
) -> tuple[str, float | None, str]:
    if current_rpe <= 0 or previous_rpe <= 0:
        return (
            "insufficient_data",
            None,
            "Noch nicht genügend RPE-Daten",
        )

    difference = round(
        current_rpe - previous_rpe,
        1,
    )

    if difference >= 0.7:
        return (
            "up",
            difference,
            "Die wahrgenommene Intensität nimmt zu",
        )

    if difference <= -0.7:
        return (
            "down",
            difference,
            "Die Einheiten werden aktuell lockerer",
        )

    return (
        "stable",
        difference,
        "Die durchschnittliche RPE bleibt stabil",
    )


def compare_dimension(
    current: dict[str, float],
    previous: dict[str, float],
    *,
    labels: dict[str, str],
    max_items: int = 4,
    minimum_current_value: float = 0.5,
    relative_threshold: float = 25.0,
) -> list[dict[str, Any]]:
    """
    Vergleicht zwei Dimensionsverteilungen und liefert nur
    die klarsten Veränderungen.
    """

    results: list[dict[str, Any]] = []
    all_keys = set(current) | set(previous)

    for key in all_keys:
        current_value = safe_float(
            current.get(key)
        )
        previous_value = safe_float(
            previous.get(key)
        )

        if (
            current_value < minimum_current_value
            and previous_value < minimum_current_value
        ):
            continue

        if previous_value <= 0:
            if current_value <= 0:
                continue

            direction = "up"
            change = None
            significance = current_value
        else:
            change = percentage_change(
                current_value,
                previous_value,
            )
            direction = classify_direction(
                change,
                stable_threshold=relative_threshold,
            )

            if direction == "stable":
                continue

            significance = abs(change or 0)

        label = labels.get(
            key,
            key.replace(
                "_",
                " ",
            ).title(),
        )

        if direction == "up":
            text = f"Mehr {label}"
        else:
            text = f"Weniger {label}"

        results.append(
            {
                "key": key,
                "label": label,
                "direction": direction,
                "symbol": direction_symbol(
                    direction
                ),
                "change_percent": change,
                "current_value": round(
                    current_value,
                    2,
                ),
                "previous_value": round(
                    previous_value,
                    2,
                ),
                "text": text,
                "_significance": significance,
            }
        )

    results.sort(
        key=lambda item: (
            item["_significance"],
            item["current_value"],
        ),
        reverse=True,
    )

    cleaned: list[dict[str, Any]] = []

    for item in results[:max_items]:
        item = dict(item)
        item.pop(
            "_significance",
            None,
        )
        cleaned.append(item)

    return cleaned


def calculate_diversity(
    training_goals: dict[str, float],
    movement_patterns: dict[str, float],
) -> dict[str, Any]:
    """
    Einfacher Diversity Score aus aktiven Trainingszielen
    und Bewegungsmustern. Der Score bewertet Vielfalt,
    nicht automatisch Trainingsqualität.
    """

    active_goals = sum(
        1
        for value in training_goals.values()
        if safe_float(value) > 0
    )
    active_patterns = sum(
        1
        for value in movement_patterns.values()
        if safe_float(value) > 0
    )

    goal_score = min(
        active_goals / 6,
        1.0,
    )
    pattern_score = min(
        active_patterns / 8,
        1.0,
    )

    score = round(
        (
            goal_score * 0.45
            + pattern_score * 0.55
        )
        * 100
    )

    if score >= 75:
        level = "high"
        text = "Hohe Trainingsvielfalt"
    elif score >= 45:
        level = "medium"
        text = "Solider Trainingsmix"
    elif score > 0:
        level = "low"
        text = "Aktuell eher einseitiger Trainingsmix"
    else:
        level = "insufficient_data"
        text = "Noch keine Trainingsvielfalt bewertbar"

    return {
        "score": score,
        "level": level,
        "text": text,
        "active_training_goals": active_goals,
        "active_movement_patterns": active_patterns,
    }


def calculate_consistency(
    history: pd.DataFrame,
    *,
    now: pd.Timestamp,
    lookback_weeks: int = 6,
) -> dict[str, Any]:
    """
    Konsistenz basiert auf aktiven Wochen, nicht auf einer
    möglichst hohen Anzahl von Einheiten.
    """

    if history.empty:
        return {
            "score": 0,
            "level": "insufficient_data",
            "active_weeks": 0,
            "lookback_weeks": lookback_weeks,
            "current_streak_weeks": 0,
            "text": (
                "Noch keine Trainingsroutine bewertbar"
            ),
        }

    active_weeks = 0
    weekly_activity: list[bool] = []

    current_week_start = (
        now.normalize()
        - pd.Timedelta(
            days=now.weekday()
        )
    )

    for index in range(lookback_weeks):
        week_end = (
            current_week_start
            - pd.Timedelta(
                weeks=index
            )
            + pd.Timedelta(
                weeks=1
            )
        )
        week_start = (
            week_end
            - pd.Timedelta(
                weeks=1
            )
        )

        sessions = history[
            (
                history[
                    "_trend_timestamp"
                ] >= week_start
            )
            & (
                history[
                    "_trend_timestamp"
                ] < week_end
            )
        ]

        is_active = not sessions.empty
        weekly_activity.append(is_active)

        if is_active:
            active_weeks += 1

    current_streak = 0

    for active in weekly_activity:
        if not active:
            break

        current_streak += 1

    score = round(
        active_weeks
        / lookback_weeks
        * 100
    )

    if score >= 85:
        level = "high"
        text = "Sehr konstante Trainingsroutine"
    elif score >= 60:
        level = "medium"
        text = "Überwiegend konstante Trainingsroutine"
    elif score > 0:
        level = "low"
        text = "Training zuletzt eher unregelmäßig"
    else:
        level = "insufficient_data"
        text = "Noch keine Trainingsroutine bewertbar"

    if current_streak >= 2:
        text = (
            f"{current_streak} Wochen "
            "hintereinander trainiert"
        )

    return {
        "score": score,
        "level": level,
        "active_weeks": active_weeks,
        "lookback_weeks": lookback_weeks,
        "current_streak_weeks": current_streak,
        "text": text,
    }



def build_trend_summary(
    trend_data: dict[str, Any],
) -> list[str]:
    """
    Erstellt eine kurze, deduplizierte Zusammenfassung
    der 14-Tage-Trends für Dashboard und Coach.
    """

    trend_block = trend_data.get(
        "trends",
        trend_data,
    )

    summary: list[str] = []

    for key in (
        "load",
        "frequency",
        "rpe",
    ):
        item = trend_block.get(
            key,
            {},
        )

        text = str(
            item.get(
                "text",
                "",
            )
        ).strip()

        if text:
            summary.append(text)

    for group_key in (
        "training_goals",
        "movement_patterns",
    ):
        for item in trend_block.get(
            group_key,
            [],
        )[:2]:
            text = str(
                item.get(
                    "text",
                    "",
                )
            ).strip()

            if text:
                summary.append(text)

    consistency_text = str(
        trend_data.get(
            "consistency",
            {},
        ).get(
            "text",
            "",
        )
    ).strip()

    diversity_text = str(
        trend_data.get(
            "diversity",
            {},
        ).get(
            "text",
            "",
        )
    ).strip()

    if consistency_text:
        summary.append(
            consistency_text
        )

    if diversity_text:
        summary.append(
            diversity_text
        )

    unique_summary: list[str] = []
    seen: set[str] = set()

    for text in summary:
        normalized = text.casefold()

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_summary.append(text)

    return unique_summary[:7]


def build_window(
    history: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, Any]:
    """
    Baut eine vollständige Kennzahlenansicht für ein
    einzelnes Zeitfenster.
    """

    period = filter_period(
        history,
        start=start,
        end=end,
    )

    return {
        **period_statistics(
            period
        ),
        "training_goals": aggregate_dimension(
            period,
            column_name=(
                DIMENSION_COLUMNS[
                    "training_goals"
                ]
            ),
        ),
        "movement_patterns": aggregate_dimension(
            period,
            column_name=(
                DIMENSION_COLUMNS[
                    "movement_patterns"
                ]
            ),
        ),
        "muscle_groups": aggregate_dimension(
            period,
            column_name=(
                DIMENSION_COLUMNS[
                    "muscle_groups"
                ]
            ),
        ),
        "load_types": aggregate_dimension(
            period,
            column_name=(
                DIMENSION_COLUMNS[
                    "load_types"
                ]
            ),
        ),
    }


def empty_trend_result(
    *,
    now: pd.Timestamp,
) -> dict[str, Any]:
    empty_history = pd.DataFrame()

    empty_load = {
        "direction": "insufficient_data",
        "symbol": "•",
        "change_percent": None,
        "current_value": 0.0,
        "previous_value": 0.0,
        "text": (
            "Noch nicht genügend Daten für "
            "einen Belastungsvergleich"
        ),
    }

    empty_frequency = {
        "direction": "insufficient_data",
        "symbol": "•",
        "change_percent": None,
        "current_sessions": 0,
        "previous_sessions": 0,
        "text": (
            "Noch keine Trainingsfrequenz "
            "erkennbar"
        ),
    }

    empty_rpe = {
        "direction": "insufficient_data",
        "symbol": "•",
        "change": None,
        "current_value": 0.0,
        "previous_value": 0.0,
        "text": "Noch nicht genügend RPE-Daten",
    }

    trends = {
        "period_days": 14,
        "comparison_text": (
            "Letzte 14 Tage vs. vorherige 14 Tage"
        ),
        "load": empty_load,
        "frequency": empty_frequency,
        "rpe": empty_rpe,
        "training_goals": [],
        "movement_patterns": [],
    }

    result = {
        "has_enough_data": False,
        "windows": {
            "7_days": {},
            "14_days": {},
            "28_days": {},
        },
        "comparison_windows": {
            "current_14_days": {},
            "previous_14_days": {},
        },
        "trends": trends,
        "diversity": calculate_diversity(
            {},
            {},
        ),
        "consistency": calculate_consistency(
            empty_history,
            now=now,
            lookback_weeks=4,
        ),
        # Kompatibilitätsfelder für bereits gebaute UI.
        "load": empty_load,
        "frequency": empty_frequency,
        "rpe": empty_rpe,
        "training_goals": [],
        "movement_patterns": [],
    }

    result["summary"] = build_trend_summary(
        result
    )

    return result


def build_trends(
    history: pd.DataFrame,
    *,
    now: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """
    Hauptfunktion der Trend-Engine.

    Zeitlogik:
    - 7 Tage: aktueller Trainingsstatus
    - 14 Tage: kurzfristige Entwicklung
    - 28 Tage: Trainingsmix, Konsistenz und Vielfalt

    Die eigentlichen Trends vergleichen:
    - letzte 14 Tage
    - vorherige 14 Tage

    Die übergebene Historie sollte bereits auf einen
    einzelnen Athleten gefiltert sein.
    """

    prepared = prepare_history(
        history
    )

    if now is None:
        now = pd.Timestamp.now(
            tz="UTC"
        )
    elif now.tzinfo is None:
        now = now.tz_localize(
            "UTC"
        )
    else:
        now = now.tz_convert(
            "UTC"
        )

    if prepared.empty:
        return empty_trend_result(
            now=now
        )

    start_7 = (
        now - pd.Timedelta(days=7)
    )
    start_14 = (
        now - pd.Timedelta(days=14)
    )
    start_28 = (
        now - pd.Timedelta(days=28)
    )
    start_previous_14 = (
        now - pd.Timedelta(days=28)
    )

    window_7 = build_window(
        prepared,
        start=start_7,
        end=now,
    )
    window_14 = build_window(
        prepared,
        start=start_14,
        end=now,
    )
    window_28 = build_window(
        prepared,
        start=start_28,
        end=now,
    )

    current_14_history = filter_period(
        prepared,
        start=start_14,
        end=now,
    )
    previous_14_history = filter_period(
        prepared,
        start=start_previous_14,
        end=start_14,
    )

    current_14_stats = period_statistics(
        current_14_history
    )
    previous_14_stats = period_statistics(
        previous_14_history
    )

    current_goals = aggregate_dimension(
        current_14_history,
        column_name=(
            DIMENSION_COLUMNS[
                "training_goals"
            ]
        ),
    )
    previous_goals = aggregate_dimension(
        previous_14_history,
        column_name=(
            DIMENSION_COLUMNS[
                "training_goals"
            ]
        ),
    )

    current_patterns = aggregate_dimension(
        current_14_history,
        column_name=(
            DIMENSION_COLUMNS[
                "movement_patterns"
            ]
        ),
    )
    previous_patterns = aggregate_dimension(
        previous_14_history,
        column_name=(
            DIMENSION_COLUMNS[
                "movement_patterns"
            ]
        ),
    )

    load_change = percentage_change(
        safe_float(
            current_14_stats[
                "total_load"
            ]
        ),
        safe_float(
            previous_14_stats[
                "total_load"
            ]
        ),
    )

    if (
        safe_float(
            previous_14_stats[
                "total_load"
            ]
        ) <= 0
        and safe_float(
            current_14_stats[
                "total_load"
            ]
        ) > 0
    ):
        load_direction = "up"
        load_text = (
            "Neue Trainingsbelastung in den "
            "letzten 14 Tagen"
        )
    else:
        load_direction = classify_direction(
            load_change,
            stable_threshold=12,
        )
        load_text = describe_load_trend(
            load_change,
            load_direction,
        )

    (
        frequency_direction,
        frequency_change,
        frequency_text,
    ) = describe_frequency_trend(
        safe_int(
            current_14_stats[
                "sessions"
            ]
        ),
        safe_int(
            previous_14_stats[
                "sessions"
            ]
        ),
    )

    (
        rpe_direction,
        rpe_change,
        rpe_text,
    ) = describe_rpe_trend(
        safe_float(
            current_14_stats[
                "average_rpe"
            ]
        ),
        safe_float(
            previous_14_stats[
                "average_rpe"
            ]
        ),
    )

    training_goal_trends = compare_dimension(
        current_goals,
        previous_goals,
        labels=TRAINING_GOAL_LABELS,
        max_items=4,
        relative_threshold=25,
    )

    movement_pattern_trends = compare_dimension(
        current_patterns,
        previous_patterns,
        labels=MOVEMENT_PATTERN_LABELS,
        max_items=4,
        relative_threshold=25,
    )

    load_trend = {
        "direction": load_direction,
        "symbol": direction_symbol(
            load_direction
        ),
        "change_percent": load_change,
        "current_value": (
            current_14_stats[
                "total_load"
            ]
        ),
        "previous_value": (
            previous_14_stats[
                "total_load"
            ]
        ),
        "text": load_text,
    }

    frequency_trend = {
        "direction": frequency_direction,
        "symbol": direction_symbol(
            frequency_direction
        ),
        "change_percent": frequency_change,
        "current_sessions": (
            current_14_stats[
                "sessions"
            ]
        ),
        "previous_sessions": (
            previous_14_stats[
                "sessions"
            ]
        ),
        "text": frequency_text,
    }

    rpe_trend = {
        "direction": rpe_direction,
        "symbol": direction_symbol(
            rpe_direction
        ),
        "change": rpe_change,
        "current_value": (
            current_14_stats[
                "average_rpe"
            ]
        ),
        "previous_value": (
            previous_14_stats[
                "average_rpe"
            ]
        ),
        "text": rpe_text,
    }

    trends = {
        "period_days": 14,
        "comparison_text": (
            "Letzte 14 Tage vs. vorherige 14 Tage"
        ),
        "load": load_trend,
        "frequency": frequency_trend,
        "rpe": rpe_trend,
        "training_goals": training_goal_trends,
        "movement_patterns": (
            movement_pattern_trends
        ),
    }

    result = {
        "has_enough_data": (
            safe_int(
                window_28[
                    "sessions"
                ]
            )
            >= 4
        ),
        "windows": {
            "7_days": window_7,
            "14_days": window_14,
            "28_days": window_28,
        },
        "comparison_windows": {
            "current_14_days": {
                **current_14_stats,
                "training_goals": current_goals,
                "movement_patterns": (
                    current_patterns
                ),
            },
            "previous_14_days": {
                **previous_14_stats,
                "training_goals": previous_goals,
                "movement_patterns": (
                    previous_patterns
                ),
            },
        },
        "trends": trends,
        "diversity": calculate_diversity(
            window_28[
                "training_goals"
            ],
            window_28[
                "movement_patterns"
            ],
        ),
        "consistency": calculate_consistency(
            filter_period(
                prepared,
                start=start_28,
                end=now,
            ),
            now=now,
            lookback_weeks=4,
        ),
        # Kompatibilitätsfelder:
        # Bestehende Dashboard-Aufrufe können zunächst
        # weiterhin trend_analysis["load"] verwenden.
        "load": load_trend,
        "frequency": frequency_trend,
        "rpe": rpe_trend,
        "training_goals": training_goal_trends,
        "movement_patterns": (
            movement_pattern_trends
        ),
    }

    result["summary"] = build_trend_summary(
        result
    )

    return result