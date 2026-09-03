import html
import re
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any
from dataclasses import asdict

import pandas as pd
from PIL import Image
import streamlit as st
from streamlit_gsheets import GSheetsConnection

from services.analysis import analyze_workout
from services.coach_logic import (
    build_positive_observations,
    build_readiness_summary,
    build_weekly_focus,
)
from services.coach import (
    build_coach_feedback,
    build_daily_tips,
)
from services.date_utils import (
    normalize_training_dates,
    format_training_dates,
    sort_training_history,
)
from services.history_analysis import analyze_history
from services.history_normalization import (
    normalize_movement_patterns,
    normalize_muscle_groups,
)
from services.parser import parse_workout
from services.trends import build_trends
from services.training_balance import build_training_balance


from ui.coach_dashboard import render_coach_dashboard, render_readiness_card
from ui.status_dashboard import render_status_dashboard

from services.history import (
    build_history_summary,
    get_user_training_history,
    remove_current_workout_from_history,
)

from services.scoring import (
    calculate_load_score,
    calculate_structural_score,
    get_level_factor,
    get_load_status,
)
from services.sheets import (
    append_workout_history,
    read_workout_history,
)
from services.utils import (
    create_stable_hash,
    format_workout_as_text,
    json_dumps_for_sheet,
    json_loads_from_sheet,
    safely_convert_to_int,
)

from ui.theme import apply_theme
from models.deterministic_analysis import DeterministicAnalysis
from models.workout_interpretation import WorkoutInterpretation
from models.training_volume import TrainingVolume


# ============================================================
# APP-KONFIGURATION
# ============================================================

import base64
from pathlib import Path
from PIL import Image


# ============================================================
# APP-KONFIGURATION
# ============================================================

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

APP_ICON_LIGHT_PATH = ASSETS_DIR / "AthletIQ_Logo_klein.png"
APP_ICON_DARK_PATH = ASSETS_DIR / "AthletIQ_Logo_klein_dunkel.png"

APP_LOGO_LIGHT_PATH = ASSETS_DIR / "AthletIQ_Logo_head.png"
APP_LOGO_DARK_PATH = ASSETS_DIR / "AthletIQ_Logo_head_dunkel_freigestellt.png"


# Browser-/App-Icon
try:
    page_icon = Image.open(APP_ICON_LIGHT_PATH)
except Exception:
    page_icon = "A"


st.set_page_config(
    page_title="AthletIQ",
    page_icon=page_icon,
    layout="wide",
)

apply_theme()


# ============================================================
# ATHLETIQ LOGO – LIGHT / DARK MODE
# ============================================================

def image_to_base64(path: Path) -> str:
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


if APP_LOGO_LIGHT_PATH.exists() and APP_LOGO_DARK_PATH.exists():

    logo_light = image_to_base64(APP_LOGO_LIGHT_PATH)
    logo_dark = image_to_base64(APP_LOGO_DARK_PATH)

    st.markdown(
        f"""
        <style>
        .athletiq-logo {{
            width: 360px;
            max-width: 100%;
            height: auto;
        }}

        .athletiq-logo-dark {{
            display: none;
        }}

        @media (prefers-color-scheme: dark) {{
            .athletiq-logo-light {{
                display: none;
            }}

            .athletiq-logo-dark {{
                display: block;
            }}
        }}
        </style>

        <div class="athletiq-logo-container">
            <img
                src="data:image/png;base64,{logo_light}"
                class="athletiq-logo athletiq-logo-light"
                alt="AthletIQ"
            >
            <img
                src="data:image/png;base64,{logo_dark}"
                class="athletiq-logo athletiq-logo-dark"
                alt="AthletIQ"
            >
        </div>
        """,
        unsafe_allow_html=True,
    )

elif APP_LOGO_LIGHT_PATH.exists():
    st.image(str(APP_LOGO_LIGHT_PATH), width=360)

elif APP_LOGO_DARK_PATH.exists():
    st.image(str(APP_LOGO_DARK_PATH), width=360)

else:
    st.title("AthletIQ")


st.caption(
    "Workout erfassen, Belastung analysieren und "
    "Trainingshistorie berücksichtigen."
)


# ============================================================
# SECRETS UND KONSTANTEN
# ============================================================

try:
    MISTRAL_API_KEY = str(
        st.secrets["MISTRAL_API_KEY"]
    ).strip()
except KeyError:
    st.error(
        "Der Eintrag `MISTRAL_API_KEY` fehlt in "
        "`.streamlit/secrets.toml`."
    )
    st.stop()

if not MISTRAL_API_KEY:
    st.error(
        "Der Mistral-API-Key in `secrets.toml` ist leer."
    )
    st.stop()


try:
    GSHEETS_CONFIG = st.secrets[
        "connections"
    ]["gsheets"]

    SHEET_URL = str(
        GSHEETS_CONFIG["spreadsheet"]
    ).strip()

except (KeyError, TypeError):
    SHEET_URL = ""


WORKSHEET_NAME = str(
    st.secrets.get(
        "GSHEETS_WORKSHEET",
        "workouts",
    )
).strip()

USERS_WORKSHEET_NAME = str(
    st.secrets.get(
        "GSHEETS_USERS_WORKSHEET",
        "users",
    )
).strip()

MISTRAL_TEXT_MODEL = str(
    st.secrets.get(
        "MISTRAL_TEXT_MODEL",
        "ministral-3b-latest",
    )
).strip()

MISTRAL_VISION_MODEL = str(
    st.secrets.get(
        "MISTRAL_VISION_MODEL",
        "pixtral-12b",
    )
).strip()

APP_TIMEZONE_NAME = str(
    st.secrets.get(
        "APP_TIMEZONE",
        "Europe/Berlin",
    )
).strip()

try:
    APP_TIMEZONE = ZoneInfo(
        APP_TIMEZONE_NAME
    )
except Exception:
    APP_TIMEZONE = ZoneInfo(
        "Europe/Berlin"
    )


SHEET_COLUMNS = [
    "zeitstempel",
    "name",
    "sportart",
    "level",
    "dauer_minuten",
    "rpe",
    "score",
    "workout",
    "verletzungen",
    "kommentar",
    "coach_feedback",
    "bewegungsmuster_json",
    "muskelgruppen_json",
    "trainingsziele_json",
    "belastungsarten_json",
    "trainingsvolumen_json",
    "klassifikation_json",
    "crossfit_movements_json",
]


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_SESSION_STATE = {
    "athleten_name": "",
    "sportart": "",
    "athleten_level": "",
    "user_profile_loaded": False,
    "verletzungen": "",
    "workout_kommentar": "",
    "aktuelles_rpe": 7,
    "trainingsdauer": 60,
    "letzter_workout_input": None,
    "letzte_workout_klassifikation": None,
    "letzte_trainingsdimensionen": None,
    "letzter_coach_text": None,
    "letzte_daily_coach_tips": None,
    "letzter_state_key": None,
    "letzter_save_key": None,
    "letzte_trainingsanalyse": None,
    "parsed_workout": None,
    "deterministic_analysis": None,
    "workout_interpretation": None,
    "coach_context_key": None,
    "coach_context_source": None,
    "original_parsed_workout": None,
    "workout_editor_open": False,
    "pending_save": False,
    "save_notice": None,
    "profiles_cache": None,
    "history_cache": None,
    "history_cache_athlete": None,
    "main_navigation": "🧠 Mein Coach",
    "coach_navigation": "Übersicht",
}

for key, default_value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# ============================================================
# GOOGLE-SHEETS-VERBINDUNG
# ============================================================

@st.cache_resource
def get_gsheets_connection():
    return st.connection(
        "gsheets",
        type=GSheetsConnection,
    )


conn = None
gsheets_error = None

if not SHEET_URL:
    gsheets_error = (
        "In `secrets.toml` fehlt "
        "`connections.gsheets.spreadsheet`."
    )
else:
    try:
        conn = get_gsheets_connection()
    except Exception as exc:
        gsheets_error = str(exc)


# ============================================================
# ATHLETENPROFILE
# ============================================================

ALLOWED_GOALS = {
    "crossfit": "CrossFit",
    "hyrox": "Hyrox",
    "running": "Running",
    "run": "Running",
    "laufen": "Running",
    "general fitness": "General Fitness",
    "general_fitness": "General Fitness",
    "abnehmen": "Abnehmen",
    "fat loss": "Abnehmen",
    "fat_loss": "Abnehmen",
}

ALLOWED_LEVELS = {
    "beginner": "Anfänger (Beginner)",
    "anfänger": "Anfänger (Beginner)",
    "anfaenger": "Anfänger (Beginner)",
    "anfänger (beginner)": "Anfänger (Beginner)",
    "intermediate": "Fortgeschritten (Intermediate)",
    "fortgeschritten": "Fortgeschritten (Intermediate)",
    "fortgeschritten (intermediate)": (
        "Fortgeschritten (Intermediate)"
    ),
    "advanced": "Experte / Elite (Advanced)",
    "experte": "Experte / Elite (Advanced)",
    "elite": "Experte / Elite (Advanced)",
    "experte / elite (advanced)": (
        "Experte / Elite (Advanced)"
    ),
}


def normalize_profile_value(
    value: object,
) -> str:
    return str(value or "").strip().casefold()


def read_user_profiles(
    *,
    conn: GSheetsConnection,
    spreadsheet_url: str,
    worksheet_name: str,
) -> pd.DataFrame:
    """
    Liest das Tabellenblatt mit den Athletenprofilen.

    Erwartete Spalten:
    username, goal, level
    """

    profiles = conn.read(
        spreadsheet=spreadsheet_url,
        worksheet=worksheet_name,
        ttl=0,
    )

    if profiles is None:
        return pd.DataFrame(
            columns=[
                "username",
                "goal",
                "level",
            ]
        )

    profiles = profiles.copy()
    profiles.columns = [
        str(column).strip().casefold()
        for column in profiles.columns
    ]

    required_columns = {
        "username",
        "goal",
        "level",
    }

    missing_columns = (
        required_columns
        - set(profiles.columns)
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )
        raise ValueError(
            "Im Tabellenblatt "
            f"„{worksheet_name}“ fehlen die Spalten: "
            f"{missing_text}."
        )

    profiles = profiles[
        [
            "username",
            "goal",
            "level",
        ]
    ].copy()

    profiles["username"] = (
        profiles["username"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    profiles = profiles[
        profiles["username"] != ""
    ].copy()

    normalized_usernames = (
        profiles["username"]
        .str.casefold()
    )

    duplicate_mask = (
        normalized_usernames.duplicated(
            keep=False
        )
    )

    if duplicate_mask.any():
        duplicate_names = sorted(
            profiles.loc[
                duplicate_mask,
                "username",
            ].unique()
        )
        raise ValueError(
            "Diese Benutzernamen sind im "
            "users-Tab mehrfach vorhanden: "
            + ", ".join(duplicate_names)
        )

    return profiles


def get_user_profile(
    profiles: pd.DataFrame,
    username: str,
) -> dict[str, str] | None:
    """
    Sucht ein Profil unabhängig von Groß-/Kleinschreibung.
    """

    normalized_username = (
        username.strip().casefold()
    )

    if (
        profiles.empty
        or not normalized_username
    ):
        return None

    matches = profiles[
        profiles["username"]
        .astype(str)
        .str.strip()
        .str.casefold()
        == normalized_username
    ]

    if matches.empty:
        return None

    row = matches.iloc[0]

    raw_goal = normalize_profile_value(
        row.get("goal")
    )
    raw_level = normalize_profile_value(
        row.get("level")
    )

    goal = ALLOWED_GOALS.get(
        raw_goal
    )
    level = ALLOWED_LEVELS.get(
        raw_level
    )

    if goal is None:
        raise ValueError(
            "Ungültiges Ziel für "
            f"„{username}“: {row.get('goal')}. "
            "Erlaubt sind CrossFit, Hyrox, Running, "
            "General Fitness und Abnehmen."
        )

    if level is None:
        raise ValueError(
            "Ungültiges Level für "
            f"„{username}“: {row.get('level')}. "
            "Erlaubt sind Beginner, Intermediate "
            "und Advanced."
        )

    return {
        "username": str(
            row.get("username")
        ).strip(),
        "goal": goal,
        "level": level,
    }


# ============================================================
# UI-HILFSFUNKTIONEN
# ============================================================

def render_status(
    status_text: str,
    status_type: str,
) -> None:
    if status_type == "success":
        st.success(
            f"🟢 STATUS: {status_text}"
        )

    elif status_type == "warning":
        st.warning(
            f"🟡 STATUS: {status_text}"
        )

    else:
        st.error(
            f"🔴 STATUS: {status_text}"
        )


def safely_float(
    value: object,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def render_balance_dimension(
    title: str,
    items: list[dict[str, Any]],
    *,
    max_rows: int = 10,
) -> None:
    """Rendert eine kompakte 28-Tage-Balance mit 14-Tage-Trend."""

    st.markdown(f"##### {title}")

    if not items:
        st.info("Für diese Trainingsdimension liegen noch keine Daten vor.")
        return

    visible_items = [
        item
        for item in items
        if item.get("status") != "no_data"
        or item.get("target_min_percent", 0) > 0
    ][:max_rows]

    table = pd.DataFrame(
        [
            {
                "Bereich": item.get("label", "–"),
                "Anteil 28 T.": (
                    f"{float(item.get('share_percent', 0)):.1f} %"
                ),
                "Zielbereich": (
                    f"{float(item.get('target_min_percent', 0)):.1f}–"
                    f"{float(item.get('target_max_percent', 0)):.1f} %"
                ),
                "Bewertung": (
                    f"{item.get('status_symbol', '•')} "
                    f"{item.get('status_label', 'Keine Daten')}"
                ),
                "Trend 14 T.": (
                    f"{item.get('trend_symbol', '→')} "
                    + (
                        f"{float(item['trend_change_percent']):+.1f} %"
                        if item.get("trend_change_percent") is not None
                        else "neu / keine Basis"
                    )
                ),
            }
            for item in visible_items
        ]
    )

    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
    )

    under = sum(
        item.get("status") == "underrepresented"
        for item in items
    )
    over = sum(
        item.get("status") == "overrepresented"
        for item in items
    )
    balanced = sum(
        item.get("status") == "balanced"
        for item in items
    )

    st.caption(
        f"{balanced} ausgewogen · {under} unterrepräsentiert · "
        f"{over} überrepräsentiert"
    )


def render_crossfit_movements(
    items: list[dict[str, Any]],
    *,
    max_rows: int = 15,
) -> None:
    """Rendert CrossFit-Skills als relativen 14-Tage-Historienvergleich."""

    st.markdown("##### CrossFit Skills")

    if not items:
        st.info("In diesem Zeitraum wurden keine CrossFit Skills erkannt.")
        return

    visible_items = items[:max_rows]

    table = pd.DataFrame(
        [
            {
                "CrossFit Skill": item.get("label", "–"),

                "Letzte 14 T.": (
                    f"{int(float(item.get('value_14', 0)))} / "
                    f"{int(item.get('sessions_14', 0))} · "
                    f"{float(item.get('share_14_percent', 0)):.1f} %"
                ),

                "Vorherige 14 T.": (
                    f"{int(float(item.get('previous_14', 0)))} / "
                    f"{int(item.get('previous_sessions_14', 0))} · "
                    f"{float(item.get('previous_share_14_percent', 0)):.1f} %"
                ),

                "Trend": (
                    f"{item.get('trend_symbol', '→')} "
                    + (
                        f"{float(item['trend_change_percent']):+.1f} %"
                        if item.get("trend_change_percent") is not None
                        else "neu / keine Basis"
                    )
                ),
            }
            for item in visible_items
        ]
    )

    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "Anteil der Workouts, in denen der jeweilige CrossFit Skill "
        "vorkam · letzte 14 Tage im Vergleich zu den vorherigen 14 Tagen."
    )


def format_workout_element_details(
    element: Any,
) -> str:
    """
    Formatiert ausschließlich die im ParsedWorkout vorhandenen
    Rohdaten eines Workout-Elements für die Anzeige.
    """

    details: list[str] = []

    sets = getattr(element, "sets", None)
    reps = getattr(element, "reps", None)

    if sets is not None and reps is not None:
        details.append(f"{sets} Sets × {reps} Reps")
    elif sets is not None:
        details.append(f"{sets} Sets")
    elif reps is not None:
        details.append(f"{reps} Reps")

    intensity = getattr(element, "intensity", None)

    if intensity is not None:
        weight = getattr(intensity, "weight", None)
        weight_unit = getattr(intensity, "weight_unit", None)

        if weight is not None:
            weight_text = f"{weight:g}" if isinstance(weight, (int, float)) else str(weight)
            if weight_unit:
                weight_text += f" {weight_unit}"
            details.append(weight_text)

        percent_1rm = getattr(intensity, "percent_1rm", None)
        if percent_1rm is not None:
            details.append(f"{percent_1rm:g} % 1RM")

        prescribed_rpe = getattr(intensity, "prescribed_rpe", None)
        if prescribed_rpe is not None:
            details.append(f"RPE {prescribed_rpe:g}")

        rir = getattr(intensity, "rir", None)
        if rir is not None:
            details.append(f"RIR {rir}")

        tempo = getattr(intensity, "tempo", None)
        if tempo:
            details.append(f"Tempo {tempo}")

    distance = getattr(element, "distance", None)
    distance_unit = getattr(element, "distance_unit", None)
    if distance is not None:
        distance_text = f"{distance:g}" if isinstance(distance, (int, float)) else str(distance)
        if distance_unit:
            distance_text += f" {distance_unit}"
        details.append(distance_text)

    speed = getattr(element, "speed", None)
    speed_unit = getattr(element, "speed_unit", None)
    if speed is not None:
        speed_text = f"{speed:g}" if isinstance(speed, (int, float)) else str(speed)
        if speed_unit:
            speed_text += f" {speed_unit}"
        details.append(speed_text)

    pace = str(getattr(element, "pace", None) or "").strip()
    pace_unit = getattr(element, "pace_unit", None)
    if pace:
        pace_text = pace
        if pace_unit:
            pace_text += f" {pace_unit}"
        details.append(pace_text)

    duration = getattr(element, "duration", None)
    duration_unit = getattr(element, "duration_unit", None)
    if duration is not None:
        duration_text = f"{duration:g}" if isinstance(duration, (int, float)) else str(duration)
        if duration_unit:
            duration_text += f" {duration_unit}"
        details.append(duration_text)

    calories = getattr(element, "calories", None)
    if calories is not None:
        details.append(f"{calories} Cal")

    notes = str(getattr(element, "notes", None) or "").strip()
    if notes:
        details.append(notes)

    return " · ".join(details)


def render_current_workout(
    parsed_workout: Any,
) -> None:
    """
    Zeigt die Struktur des ParsedWorkout vollständig genug für
    eine visuelle Kontrolle nach Text- oder Fotoeingabe.
    """

    for segment in parsed_workout.segments:
        segment_type = str(getattr(segment, "type", "") or "").strip()
        segment_type_labels = {
            "rep_scheme": "Wiederholungsschema",
            "rounds": "Runden",
            "cardio": "Cardio",
        }

        display_segment_type = segment_type_labels.get(
            segment_type,
            segment_type,
        )
        segment_name = str(getattr(segment, "name", "") or "").strip()

        if (
            segment_name
            and display_segment_type
            and segment_name.casefold()
            != display_segment_type.casefold()
        ):
            heading = (
                f"{segment_name} · "
                f"{display_segment_type}"
            )
        else:
            heading = (
                segment_name
                or display_segment_type
                or "Workout"
            )

        st.markdown(f"#### {heading}")

        segment_details: list[str] = []

        rounds = getattr(segment, "rounds", None)
        if rounds is not None:
            segment_details.append(f"{rounds} Runden")

        rep_scheme = getattr(segment, "rep_scheme", None)
        if rep_scheme:
            rep_scheme_text = "-".join(
                str(rep) for rep in rep_scheme
            )
            segment_details.append(rep_scheme_text)

        time_cap = getattr(segment, "time_cap_minutes", None)
        if time_cap is not None:
            segment_details.append(f"Time Cap: {time_cap} Min.")

        segment_notes = str(getattr(segment, "notes", None) or "").strip()
        if segment_notes:
            segment_details.append(segment_notes)

        if segment_details:
            st.caption(" · ".join(segment_details))

        if not segment.elements:
            st.caption("Keine einzelnen Workout-Elemente erkannt.")
            continue

        for element in segment.elements:
            exercise_name = (
                getattr(element.movement, "raw_name", None)
                or getattr(element.movement, "canonical_name", None)
                or "Unbekannte Übung"
            )

            exercise_details = format_workout_element_details(element)

            if exercise_details:
                st.markdown(
                    f"- **{exercise_name}** — {exercise_details}"
                )
            else:
                st.markdown(f"- **{exercise_name}**")




def optional_duration_input(
    label: str,
    value: int | float | None,
    *,
    key: str,
) -> float | None:
    """
    Editiert optionale Zeitangaben und normalisiert sie auf Minuten.

    Erlaubt z. B.:
    4.5
    4,5
    4:30
    4 min 30 Sekunden
    90 Sekunden
    1 h 15 min

    Leeres Feld bedeutet None.
    """

    if value is None:
        current_value = ""
    else:
        current_value = f"{value:g}" if isinstance(value, (int, float)) else str(value)

    raw_value = st.text_input(
        label,
        value=current_value,
        key=key,
        placeholder="z. B. 4:30 oder 4 min 30 Sekunden",
    ).strip()

    if not raw_value:
        return None

    normalized = (
        raw_value.casefold()
        .replace(",", ".")
        .replace("stunden", "h")
        .replace("stunde", "h")
        .replace("std.", "h")
        .replace("std", "h")
        .replace("minutes", "min")
        .replace("minute", "min")
        .replace("minuten", "min")
        .replace("seconds", "sec")
        .replace("second", "sec")
        .replace("sekunden", "sec")
        .replace("sekunde", "sec")
        .replace("secs", "sec")
        .replace("sek", "sec")
        .strip()
    )

    # Reine Zahl: wie bisher als Minuten interpretieren.
    try:
        return float(normalized)
    except ValueError:
        pass

    # mm:ss bzw. hh:mm:ss
    colon_match = re.fullmatch(
        r"\s*(\d+):([0-5]?\d)(?::([0-5]?\d))?\s*",
        normalized,
    )
    if colon_match:
        first = int(colon_match.group(1))
        second = int(colon_match.group(2))
        third = colon_match.group(3)

        if third is None:
            return first + second / 60

        return first * 60 + second + int(third) / 60

    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*h\b", normalized)
    minute_match = re.search(r"(\d+(?:\.\d+)?)\s*min\b", normalized)
    second_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sec|s)\b", normalized)

    if hour_match or minute_match or second_match:
        hours = float(hour_match.group(1)) if hour_match else 0.0
        minutes = float(minute_match.group(1)) if minute_match else 0.0
        seconds = float(second_match.group(1)) if second_match else 0.0

        return hours * 60 + minutes + seconds / 60

    st.warning(
        f"„{label}“ konnte nicht als Dauer erkannt werden. "
        "Nutze z. B. 4:30, 4 min 30 Sekunden, 90 Sekunden "
        "oder 1 h 15 min."
    )
    return value


def optional_number_input(
    label: str,
    value: int | float | None,
    *,
    key: str,
    step: int | float = 1,
) -> int | float | None:
    """
    Editiert optionale Zahlenwerte. Ein leeres Feld bedeutet None.
    """

    raw_value = st.text_input(
        label,
        value="" if value is None else str(value),
        key=key,
    ).strip()

    if not raw_value:
        return None

    try:
        number = float(raw_value.replace(",", "."))
    except ValueError:
        st.warning(f"„{label}“ muss eine Zahl oder leer sein.")
        return value

    if isinstance(step, int):
        return int(number)

    return number

def optional_rep_scheme_input(
    label: str,
    value: list[int] | None,
    *,
    key: str,
) -> list[int] | None:
    """
    Editiert ein Wiederholungsschema wie 21-15-9.

    Leeres Feld bedeutet None.
    Erlaubt z. B.:
    21-15-9
    21,15,9
    21 15 9
    """

    current_value = (
        "-".join(str(rep) for rep in value)
        if value
        else ""
    )

    raw_value = st.text_input(
        label,
        value=current_value,
        key=key,
        placeholder="z. B. 21-15-9",
    ).strip()

    if not raw_value:
        return None

    normalized = (
        raw_value
        .replace(",", "-")
        .replace(" ", "-")
    )

    parts = [
        part.strip()
        for part in normalized.split("-")
        if part.strip()
    ]

    try:
        rep_scheme = [
            int(part)
            for part in parts
        ]
    except ValueError:
        st.warning(
            f"„{label}“ muss aus positiven ganzen Zahlen "
            "bestehen, z. B. 21-15-9."
        )
        return value

    if (
        not rep_scheme
        or any(rep <= 0 for rep in rep_scheme)
    ):
        st.warning(
            f"„{label}“ darf nur positive "
            "Wiederholungszahlen enthalten."
        )
        return value

    return rep_scheme

def render_workout_editor(
    parsed_workout: Any,
) -> bool:
    """
    Struktureller Editor für das aktuell erkannte ParsedWorkout.

    Rückgabe:
        True, wenn Änderungen übernommen wurden.
    """

    st.markdown("### Workout bearbeiten")
    st.caption(
        "Entferne nicht absolvierte Scaling-Optionen oder korrigiere "
        "erkannte Werte. Nur die übernommene Version wird anschließend "
        "analysiert und gespeichert."
    )

    segments_to_delete: set[int] = set()
    elements_to_delete: dict[int, set[int]] = {}
    edited_values: dict[tuple, Any] = {}

    for segment_index, segment in enumerate(parsed_workout.segments):
        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])

            with top_left:
                segment_name = st.text_input(
                    "Segmentname",
                    value=str(segment.name or ""),
                    key=f"edit_segment_name_{segment_index}",
                )
                segment_type = st.text_input(
                    "Workoutart / Segmenttyp",
                    value=str(segment.type or ""),
                    key=f"edit_segment_type_{segment_index}",
                )

            with top_right:
                delete_segment = st.checkbox(
                    "Segment löschen",
                    key=f"delete_segment_{segment_index}",
                )
                if delete_segment:
                    segments_to_delete.add(segment_index)

            rounds = optional_number_input(
                "Runden",
                segment.rounds,
                key=f"edit_rounds_{segment_index}",
                step=1,
            )
            rep_scheme = optional_rep_scheme_input(
                "Wiederholungsschema",
                getattr(segment, "rep_scheme", None),
                key=f"edit_rep_scheme_{segment_index}",
            )
            time_cap = optional_number_input(
                "Time Cap (Min.)",
                segment.time_cap_minutes,
                key=f"edit_time_cap_{segment_index}",
                step=1,
            )
            segment_notes = st.text_input(
                "Segment-Notiz",
                value=str(segment.notes or ""),
                key=f"edit_segment_notes_{segment_index}",
            )

            edited_values[("segment", segment_index)] = {
                "name": segment_name.strip() or None,
                "type": segment_type.strip() or "unknown",
                "rounds": rounds,
                "rep_scheme": rep_scheme,
                "time_cap_minutes": time_cap,
                "notes": segment_notes.strip() or None,
            }

            st.markdown("**Movements**")

            for element_index, element in enumerate(segment.elements):
                with st.expander(
                    (
                        element.movement.raw_name
                        or element.movement.canonical_name
                        or f"Movement {element_index + 1}"
                    ),
                    expanded=False,
                ):
                    delete_element = st.checkbox(
                        "Movement löschen",
                        key=f"delete_element_{segment_index}_{element_index}",
                    )
                    if delete_element:
                        elements_to_delete.setdefault(
                            segment_index, set()
                        ).add(element_index)

                    movement_name = st.text_input(
                        "Movement",
                        value=str(element.movement.raw_name or ""),
                        key=f"edit_movement_{segment_index}_{element_index}",
                    )

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        sets = optional_number_input(
                            "Sets",
                            element.sets,
                            key=f"edit_sets_{segment_index}_{element_index}",
                            step=1,
                        )
                        reps = optional_number_input(
                            "Reps",
                            element.reps,
                            key=f"edit_reps_{segment_index}_{element_index}",
                            step=1,
                        )
                    with col2:
                        weight = optional_number_input(
                            "Gewicht",
                            element.intensity.weight,
                            key=f"edit_weight_{segment_index}_{element_index}",
                            step=0.5,
                        )
                        weight_unit = st.text_input(
                            "Gewichtseinheit",
                            value=str(element.intensity.weight_unit or ""),
                            key=f"edit_weight_unit_{segment_index}_{element_index}",
                        )
                    with col3:
                        distance = optional_number_input(
                            "Distanz",
                            element.distance,
                            key=f"edit_distance_{segment_index}_{element_index}",
                            step=1.0,
                        )
                        distance_unit = st.text_input(
                            "Distanzeinheit",
                            value=str(element.distance_unit or ""),
                            key=f"edit_distance_unit_{segment_index}_{element_index}",
                        )

                    pace_col, speed_col = st.columns(2)
                    with pace_col:
                        pace = st.text_input(
                            "Pace",
                            value=str(getattr(element, "pace", None) or ""),
                            placeholder="z. B. 5:00",
                            key=f"edit_pace_{segment_index}_{element_index}",
                        )
                        pace_unit = st.text_input(
                            "Pace-Einheit",
                            value=str(getattr(element, "pace_unit", None) or ""),
                            placeholder="min/km",
                            key=f"edit_pace_unit_{segment_index}_{element_index}",
                        )

                    with speed_col:
                        speed = optional_number_input(
                            "Geschwindigkeit",
                            getattr(element, "speed", None),
                            key=f"edit_speed_{segment_index}_{element_index}",
                            step=0.1,
                        )
                        speed_unit = st.text_input(
                            "Geschwindigkeitseinheit",
                            value=str(getattr(element, "speed_unit", None) or ""),
                            placeholder="km/h",
                            key=f"edit_speed_unit_{segment_index}_{element_index}",
                        )

                    duration = optional_duration_input(
                        "Dauer",
                        element.duration,
                        key=f"edit_duration_{segment_index}_{element_index}",
                    )
                    duration_unit = st.text_input(
                        "Dauereinheit",
                        value=str(element.duration_unit or ""),
                        key=f"edit_duration_unit_{segment_index}_{element_index}",
                    )
                    calories = optional_number_input(
                        "Calories",
                        element.calories,
                        key=f"edit_calories_{segment_index}_{element_index}",
                        step=1,
                    )
                    notes = st.text_input(
                        "Movement-Notiz",
                        value=str(element.notes or ""),
                        key=f"edit_element_notes_{segment_index}_{element_index}",
                    )

                    edited_values[
                        ("element", segment_index, element_index)
                    ] = {
                        "movement": movement_name.strip(),
                        "sets": sets,
                        "reps": reps,
                        "weight": weight,
                        "weight_unit": weight_unit.strip() or None,
                        "distance": distance,
                        "distance_unit": distance_unit.strip() or None,
                        "speed": speed,
                        "speed_unit": speed_unit.strip() or None,
                        "pace": pace.strip() or None,
                        "pace_unit": pace_unit.strip() or None,
                        "duration": duration,
                        "duration_unit": duration_unit.strip() or None,
                        "calories": calories,
                        "notes": notes.strip() or None,
                    }

    apply_col, restore_col, cancel_col = st.columns(3)

    apply_clicked = apply_col.button(
        "Änderungen übernehmen",
        type="primary",
        width="stretch",
        key="apply_workout_edits",
    )
    restore_clicked = restore_col.button(
        "Original wiederherstellen",
        width="stretch",
        key="restore_original_workout",
    )
    cancel_clicked = cancel_col.button(
        "Abbrechen",
        width="stretch",
        key="cancel_workout_edits",
    )

    if restore_clicked:
        original = st.session_state.get("original_parsed_workout")
        if original is not None:
            st.session_state["parsed_workout"] = deepcopy(original)
            st.session_state["workout_editor_open"] = False
            st.session_state["letzter_coach_text"] = None
            st.session_state["letzter_state_key"] = None
            st.session_state["letzter_save_key"] = None
            st.session_state["pending_save"] = False
            st.rerun()

    if cancel_clicked:
        st.session_state["workout_editor_open"] = False
        st.rerun()

    if not apply_clicked:
        return False

    for segment_index, segment in enumerate(parsed_workout.segments):
        if segment_index in segments_to_delete:
            continue

        values = edited_values[("segment", segment_index)]
        segment.name = values["name"]
        segment.type = values["type"]
        segment.rounds = values["rounds"]
        segment.rep_scheme = values["rep_scheme"]
        segment.time_cap_minutes = values["time_cap_minutes"]
        segment.notes = values["notes"]

        kept_elements = []

        for element_index, element in enumerate(segment.elements):
            if element_index in elements_to_delete.get(segment_index, set()):
                continue

            values = edited_values[
                ("element", segment_index, element_index)
            ]

            element.movement.raw_name = values["movement"]
            element.movement.canonical_name = values["movement"]
            element.sets = values["sets"]
            element.reps = values["reps"]
            element.intensity.weight = values["weight"]
            element.intensity.weight_unit = values["weight_unit"]
            element.distance = values["distance"]
            element.distance_unit = values["distance_unit"]
            element.speed = values["speed"]
            element.speed_unit = values["speed_unit"]
            element.pace = values["pace"]
            element.pace_unit = values["pace_unit"]
            element.duration = values["duration"]
            element.duration_unit = values["duration_unit"]
            element.calories = values["calories"]
            element.notes = values["notes"]

            kept_elements.append(element)

        segment.elements = kept_elements

    parsed_workout.segments = [
        segment
        for index, segment in enumerate(parsed_workout.segments)
        if index not in segments_to_delete
    ]

    if not parsed_workout.segments:
        st.error("Das Workout muss mindestens ein Segment enthalten.")
        return False

    if not any(segment.elements for segment in parsed_workout.segments):
        st.error("Das Workout muss mindestens ein Movement enthalten.")
        return False

    st.session_state["parsed_workout"] = parsed_workout
    st.session_state["workout_editor_open"] = False
    st.session_state["letzter_coach_text"] = None
    st.session_state["letzter_state_key"] = None
    st.session_state["letzter_save_key"] = None
    st.session_state["pending_save"] = False

    return True


def reset_current_workout() -> None:
    st.session_state[
        "letzter_workout_input"
    ] = None
    
    st.session_state[
        "letzte_workout_klassifikation"
    ] = None

    st.session_state[
        "letzte_trainingsdimensionen"
    ] = None

    st.session_state[
        "letzter_coach_text"
    ] = None

    st.session_state[
        "letzter_state_key"
    ] = None

    st.session_state[
        "letzter_save_key"
    ] = None

    st.session_state[
        "letzte_trainingsanalyse"
    ] = None

    st.session_state[
        "parsed_workout"
    ] = None
    
    st.session_state[
        "original_parsed_workout"
    ] = None

    st.session_state[
        "workout_editor_open"
    ] = False

    st.session_state[
        "deterministic_analysis"
    ] = None

    st.session_state[
        "workout_interpretation"
    ] = None

    st.session_state[
        "pending_save"
    ] = False

    st.session_state[
        "save_notice"
    ] = None

    st.session_state[
        "workout_kommentar"
    ] = ""

    st.session_state[
        "aktuelles_rpe"
    ] = 7

    st.session_state[
        "trainingsdauer"
    ] = 60


# ============================================================
# STATUS-HILFSFUNKTIONEN
# ============================================================

def summarize_balance_dimension(
    items: list[dict],
    *,
    empty_text: str,
) -> str:
    """
    Erstellt einen kurzen Absatz für den Tab 'Mein Status'.
    Die vollständigen Einzelwerte bleiben im Tab
    'Trainingsdetails'.
    """

    valid_items = [
        item
        for item in (items or [])
        if item.get("status") != "no_data"
    ]

    if not valid_items:
        return empty_text

    under = [
        item for item in valid_items
        if item.get("status") == "underrepresented"
    ]
    over = [
        item for item in valid_items
        if item.get("status") == "overrepresented"
    ]
    balanced = [
        item for item in valid_items
        if item.get("status") == "balanced"
    ]

    def names(values: list[dict], limit: int = 2) -> str:
        labels = [
            str(item.get("label", "")).strip()
            for item in values[:limit]
            if str(item.get("label", "")).strip()
        ]
        return ", ".join(labels)

    parts: list[str] = []

    if balanced:
        parts.append(
            f"{len(balanced)} Bereiche liegen im Zielkorridor"
        )

    if under:
        parts.append(
            "unterrepräsentiert sind "
            + names(under)
        )

    if over:
        parts.append(
            "überrepräsentiert sind "
            + names(over)
        )

    if not parts:
        return (
            "Für diesen Bereich ist aktuell noch keine "
            "eindeutige Einordnung möglich."
        )

    sentence = "; ".join(parts)
    return sentence[0].upper() + sentence[1:] + "."


def _filter_cached_history(history: pd.DataFrame, athlete_name: str, days: int | None = None) -> pd.DataFrame:
    """Filtert den einmal geladenen Sheet-Stand lokal, ohne weiteren API-Read."""
    if history is None or history.empty or not athlete_name.strip():
        return pd.DataFrame(columns=SHEET_COLUMNS)
    normalized_names = history["name"].fillna("").astype(str).str.strip().str.casefold()
    result = history[normalized_names == athlete_name.strip().casefold()].copy()
    if result.empty:
        return pd.DataFrame(columns=SHEET_COLUMNS)
    result["zeitstempel_parsed"] = pd.to_datetime(result["zeitstempel"], errors="coerce", utc=True)
    if days is not None:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
        result = result[result["zeitstempel_parsed"].notna() & (result["zeitstempel_parsed"] >= cutoff)].copy()
    result["rpe_numeric"] = pd.to_numeric(result["rpe"], errors="coerce")
    result["score_numeric"] = pd.to_numeric(result["score"], errors="coerce")
    result["dauer_numeric"] = pd.to_numeric(result["dauer_minuten"], errors="coerce")
    return result.sort_values("zeitstempel_parsed", ascending=True)


# ============================================================
# GLOBALER ATHLETENKONTEXT
# ============================================================

header_name_col, header_action_col = st.columns([5, 1])
with header_name_col:
    user_name = st.text_input(
        "Athletenprofil",
        value=st.session_state["athleten_name"],
        placeholder="Athletenname eingeben",
        label_visibility="collapsed",
        help="Ziel und Level werden automatisch aus dem Tabellenblatt „users“ geladen.",
    ).strip()

st.session_state["athleten_name"] = user_name
profile_error = None
user_profile = None
if user_name:
    if conn is None:
        profile_error = "Das Athletenprofil kann nicht geladen werden, weil Google Sheets nicht verbunden ist."
    else:
        try:
            if st.session_state.get("profiles_cache") is None:
                st.session_state["profiles_cache"] = read_user_profiles(
                    conn=conn, spreadsheet_url=SHEET_URL, worksheet_name=USERS_WORKSHEET_NAME
                )
            user_profiles = st.session_state["profiles_cache"]
            user_profile = get_user_profile(user_profiles, user_name)
        except Exception as exc:
            profile_error = str(exc)

if user_profile is not None:
    user_name = user_profile["username"]
    sportart = user_profile["goal"]
    level = user_profile["level"]
    st.session_state["athleten_name"] = user_name
    st.session_state["sportart"] = sportart
    st.session_state["athleten_level"] = level
    st.session_state["user_profile_loaded"] = True

    # Google Sheets nur einmal pro Athlet/Sitzung lesen. Alle Views arbeiten
    # anschließend mit demselben lokalen DataFrame.
    history_cache_key = user_name.strip().casefold()
    if st.session_state.get("history_cache_athlete") != history_cache_key:
        try:
            st.session_state["history_cache"] = read_workout_history(
                conn=conn, spreadsheet_url=SHEET_URL, worksheet_name=WORKSHEET_NAME, columns=SHEET_COLUMNS
            )
            st.session_state["history_cache_athlete"] = history_cache_key
        except Exception as exc:
            st.session_state["history_cache"] = pd.DataFrame(columns=SHEET_COLUMNS)
            profile_error = f"Die Trainingshistorie konnte nicht geladen werden: {exc}"

    with header_name_col:
        st.caption(f"{sportart} · {level}")
else:
    sportart = ""
    level = ""
    st.session_state["sportart"] = ""
    st.session_state["athleten_level"] = ""
    st.session_state["user_profile_loaded"] = False
    if profile_error:
        st.error(profile_error)
    elif user_name:
        st.warning("Dieser Benutzername wurde im Tabellenblatt „users“ nicht gefunden.")


if user_profile is not None:
    first_name = user_name.split()[0] if user_name else "Athlet"
    st.markdown(f"### Guten Morgen, {first_name} 👋")

with header_action_col:
    if st.button(
        "＋ Neues Training",
        key="global_new_workout",
        type="primary",
        width="stretch",
        disabled=user_profile is None,
        help="Training per Foto oder Text erfassen",
    ):
        st.session_state["workout_entry_requested"] = True

        # Globale Navigation direkt zur Eingabemaske führen.
        st.session_state["main_navigation"] = "🧠 Mein Coach"
        st.session_state["coach_navigation"] = "Übersicht"

        st.rerun()

# ============================================================
# HAUPTNAVIGATION
# ============================================================

main_coach, main_training = st.tabs(
    ["🧠 Mein Coach", "🏋️ Training"],
    key="main_navigation",
    on_change="rerun",
)

with main_coach:
    tab0, tab4, tab2 = st.tabs(
        ["Übersicht", "Analyse", "Einordnung"],
        key="coach_navigation",
        on_change="rerun",
    )

tab3 = main_training

# ============================================================
# MEIN COACH · ÜBERSICHT
# ============================================================

with tab0:
    if not user_name:
        st.info("Gib oben deinen Benutzernamen ein. Danach werden Status, Coach und Historie für dein Profil geladen.")
    elif user_profile is None:
        st.info("Für die App muss ein gültiges Athletenprofil geladen sein.")
    else:
        # Statusdaten immer direkt aus der gespeicherten Historie laden.
        # Dadurch sind „Letzte Einheit“ und „Deine Entwicklung“ bereits
        # beim Öffnen der App sinnvoll befüllt und nicht von einer Analyse
        # in der aktuellen Sitzung abhängig.
        try:
            status_history = _filter_cached_history(
                st.session_state.get("history_cache"), user_name, days=28
            )
        except Exception as exc:
            status_history = pd.DataFrame(columns=SHEET_COLUMNS)
            st.warning(f"Die Trainingshistorie konnte nicht geladen werden: {exc}")

        # Coach-Kontext direkt aus den bereits gespeicherten Analyse-JSONs laden.
        # Wichtig: Ein gespeichertes Workout wird hier NICHT erneut durch Mistral
        # geparst oder interpretiert. Das vermeidet teure Netzwerkaufrufe bei
        # Athletenwahl und normalen Streamlit-Reruns.
        if not status_history.empty:
            latest_for_coach = sort_training_history(status_history).iloc[0]
            latest_stamp = str(latest_for_coach.get("zeitstempel", ""))
            latest_workout_text = str(latest_for_coach.get("workout", "") or "").strip()
            coach_context_key = create_stable_hash({
                "athlete": user_name.casefold(),
                "timestamp": latest_stamp,
                "workout": latest_workout_text,
            })

            if st.session_state.get("coach_context_key") != coach_context_key:
                try:
                    volume_data = json_loads_from_sheet(
                        latest_for_coach.get("trainingsvolumen_json")
                    ) or {}
                    if not isinstance(volume_data, dict):
                        volume_data = {}

                    latest_analysis = DeterministicAnalysis(
                        bewegungsmuster=json_loads_from_sheet(
                            latest_for_coach.get("bewegungsmuster_json")
                        ) or {},
                        muskelgruppen=json_loads_from_sheet(
                            latest_for_coach.get("muskelgruppen_json")
                        ) or {},
                        movements=json_loads_from_sheet(
                            latest_for_coach.get("crossfit_movements_json")
                        ) or {},
                        trainingsziele=json_loads_from_sheet(
                            latest_for_coach.get("trainingsziele_json")
                        ) or {},
                        belastungsarten=json_loads_from_sheet(
                            latest_for_coach.get("belastungsarten_json")
                        ) or {},
                        trainingsvolumen=TrainingVolume(
                            **{
                                key: value
                                for key, value in volume_data.items()
                                if key in TrainingVolume.__dataclass_fields__
                            }
                        ),
                    )

                    latest_interpretation = WorkoutInterpretation(
                        klassifikation=json_loads_from_sheet(
                            latest_for_coach.get("klassifikation_json")
                        ) or {},
                    )

                    # parsed_workout bleibt bei History-Kontext bewusst leer. Es wird
                    # nur für ein neu erfasstes Workout benötigt.
                    st.session_state["parsed_workout"] = None
                    st.session_state["deterministic_analysis"] = latest_analysis
                    st.session_state["workout_interpretation"] = latest_interpretation
                    st.session_state["aktuelles_rpe"] = safely_convert_to_int(
                        latest_for_coach.get("rpe"), default=7
                    )
                    st.session_state["trainingsdauer"] = safely_convert_to_int(
                        latest_for_coach.get("dauer_minuten"), default=60
                    )
                    st.session_state["verletzungen"] = str(
                        latest_for_coach.get("verletzungen", "") or ""
                    )
                    st.session_state["workout_kommentar"] = str(
                        latest_for_coach.get("kommentar", "") or ""
                    )
                    st.session_state["letzter_coach_text"] = str(
                        latest_for_coach.get("coach_feedback", "") or ""
                    ).strip() or None
                    st.session_state["coach_context_key"] = coach_context_key
                    st.session_state["coach_context_source"] = "history_cached"
                except Exception as exc:
                    st.warning(
                        "Die gespeicherten Analysedaten der letzten Einheit konnten "
                        f"nicht vollständig geladen werden: {exc}"
                    )
        else:
            st.session_state["coach_context_key"] = create_stable_hash({
                "athlete": user_name.casefold(), "empty": True
            })
            st.session_state["coach_context_source"] = "history_empty"

        history_summary = build_history_summary(status_history, period_days=28)
        trend_analysis = build_trends(status_history)

        # ------------------------------------------------------------
        # Coach-Status aus der aktuellen 28-Tage-Historie ableiten
        # ------------------------------------------------------------

        status_training_analysis = analyze_history(
            history_summary=history_summary,
        )

        status_training_balance = build_training_balance(
            trend_analysis,
            primary_goal=sportart,
        )

        status_readiness = status_training_analysis.readiness
        st.session_state["status_readiness"] = status_readiness

        status_positive = build_positive_observations(
            history_summary=history_summary,
            training_analysis=status_training_analysis,
        )

        status_focus = build_weekly_focus(
            history_summary=history_summary,
            training_analysis=status_training_analysis,
            primary_goal=sportart,
            training_balance=status_training_balance,
        )

        recent_sessions = history_summary.get("letzte_einheiten", []) or []
        latest_session = recent_sessions[-1] if recent_sessions else {}
        latest_name = str(latest_session.get("sportart") or "Letzte erfasste Einheit").strip()
        latest_workout_text = str(latest_session.get("workout") or "").strip()
        if latest_workout_text:
            first_line = latest_workout_text.splitlines()[0].strip()
            if first_line and len(first_line) <= 80:
                latest_name = first_line

        latest_meta_parts = []
        if latest_session.get("zeitstempel"):
            latest_meta_parts.append(str(latest_session["zeitstempel"]))
        if latest_session.get("dauer_minuten"):
            latest_meta_parts.append(f"{latest_session['dauer_minuten']} min")
        if latest_session.get("rpe"):
            latest_meta_parts.append(f"RPE {latest_session['rpe']}")
        latest_meta = " · ".join(latest_meta_parts) if latest_meta_parts else "Noch keine gespeicherte Einheit vorhanden"

        if not st.session_state.get("workout_entry_requested", False):
            st.markdown(
                (
                    '<div class="welcome-card">'
                    f'<div class="welcome-title">Willkommen zurück, {html.escape(str(user_name or "Athlet"))}</div>'
                    f'<div>{html.escape(str(sportart or "Sport"))} &nbsp;·&nbsp; '
                    f'{html.escape(str(level or "Level"))} &nbsp;·&nbsp; '
                    f'{int(history_summary.get("anzahl_einheiten", 0) or 0)} Workouts in 28 Tagen</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )
            render_status_dashboard(
                user_name=user_name,
                sessions_28=int(history_summary.get("anzahl_einheiten", 0) or 0),
                readiness=status_readiness,
                positive_observations=status_positive,
                weekly_focus=status_focus,
                load_trend=trend_analysis.get("load", {}),
                consistency=trend_analysis.get("consistency", {}),
                diversity=trend_analysis.get("diversity", {}),
                latest_workout_name=latest_name,
                latest_workout_meta=latest_meta,
                trend_analysis=trend_analysis,
                recent_sessions=recent_sessions,
            )
# ============================================================
# TAB 1: WORKOUT EINTRAGEN
# ============================================================

with tab0:
    if st.session_state.get("workout_entry_requested", False) and user_profile is not None:
        st.markdown("---")
        top_left, top_right = st.columns([4, 1])
        with top_left:
            st.markdown("## Neues Training")
            st.caption("Erfasse dein Workout per Foto oder Text. Die Erkennung kannst du vor dem Speichern wie gewohnt prüfen und anpassen.")
        with top_right:
            if st.button("← Zurück", key="close_workout_entry", width="stretch"):
                st.session_state["workout_entry_requested"] = False
                st.rerun()

        injuries = st.text_area(
            "Aktuelle Einschränkungen oder Verletzungen",
            value=st.session_state[
                "verletzungen"
            ],
            placeholder=(
                "z. B. leichtes Ziehen im unteren Rücken, "
                "Knieschmerzen links bei Squats oder "
                "müde Schultern"
            ),
            help=(
                "Diese Angaben werden bei der "
                "Trainings- und Historienanalyse berücksichtigt."
            ),
        )

        st.session_state[
            "verletzungen"
        ] = injuries.strip()

        st.markdown("---")

        if not user_name:
            st.info(
                "Bitte gib zuerst deinen "
                "Benutzernamen ein."
            )

        elif user_profile is None:
            st.info(
                "Für die Workout-Eingabe muss ein "
                "gültiges Athletenprofil geladen sein."
            )

        else:
            st.markdown("### Wie möchtest du dein Training eintragen?")
            input_type = st.radio(
                "Eingabeart",
                ["📷 Foto", "✎ Text"],
                horizontal=True,
                label_visibility="collapsed",
            )

            should_analyze = False
            workout_text_input = ""
            photo = None
            model_to_use = (
                MISTRAL_TEXT_MODEL
            )

            content_payload = ""
            if (
                input_type
                == "📷 Foto"
            ):
                photo = st.camera_input(
                    "Fotografiere das Whiteboard, "
                    "einen Zettel oder dein Display"
                )

                should_analyze = st.button(
                    "📷 Foto analysieren",
                    disabled=photo is None,
                    type="primary",
                    width="stretch",
                )

                if (
                    should_analyze
                    and photo is not None
                ):
                    mime_type = (
                        getattr(
                            photo,
                            "type",
                            None,
                        )
                        or "image/jpeg"
                    )


            else:
                workout_text_input = (
                    st.text_area(
                        "Workout hier eintragen",
                        placeholder=(
                            "Beispiel:\n"
                            "Strength: Deadlift 4 × 3\n\n"
                            "Workout: 5 RFT\n"
                            "300 m Row\n"
                            "6 Burpees\n"
                            "12 Deadlifts"
                        ),
                        height=220,
                    )
                )

                should_analyze = st.button(
                    "🧠 Workout analysieren",
                    disabled=not (
                        workout_text_input.strip()
                    ),
                    type="primary",
                    width="stretch",
                )


            if should_analyze:
                with st.spinner(
                    "Workout wird strukturiert "
                    "und geprüft ..."
                ):
                    try:
                        if (
                            input_type
                            == "📷 Foto"
                        ):
                            parsed_workout = parse_workout(
                                image_data=photo.getvalue(),
                                image_mime_type=(
                                    getattr(photo, "type", None)
                                    or "image/jpeg"
                                ),
                                api_key=MISTRAL_API_KEY,
                                model=MISTRAL_VISION_MODEL,
                            )
                        else:
                            parsed_workout = parse_workout(
                                workout_text=workout_text_input.strip(),
                                api_key=MISTRAL_API_KEY,
                                model=MISTRAL_TEXT_MODEL,
                            )

                        deterministic_analysis, workout_interpretation = analyze_workout(
                            parsed_workout=parsed_workout,
                            sportart=sportart,
                            api_key=MISTRAL_API_KEY,
                            model=MISTRAL_TEXT_MODEL,
                        )

                        st.session_state["parsed_workout"] = parsed_workout
                        st.session_state["original_parsed_workout"] = deepcopy(
                            parsed_workout
                        )
                        st.session_state["workout_editor_open"] = False
                        st.session_state["deterministic_analysis"] = deterministic_analysis
                        st.session_state["workout_interpretation"] = workout_interpretation

                        st.session_state["letzter_coach_text"] = None
                        st.session_state["letzter_state_key"] = None
                        st.session_state["letzter_save_key"] = None

                        st.success("Workout erfolgreich analysiert.")

                    except (
                        RuntimeError,
                        ValueError,
                    ) as exc:

                        st.error(
                            "Analyse fehlgeschlagen: "
                            f"{exc}"
                        )


            current_workout = st.session_state.get(
                "parsed_workout"
            )

            if current_workout:
                st.markdown("---")
                st.write(
                    "### Aktuell erfasstes Training"
                )

                render_current_workout(
                    current_workout
                )

                if st.button(
                    "✏️ Workout bearbeiten",
                    width="stretch",
                    key="open_workout_editor",
                ):
                    st.session_state["workout_editor_open"] = True

                if st.session_state.get("workout_editor_open"):
                    changes_applied = render_workout_editor(
                        current_workout
                    )

                    if changes_applied:
                        with st.spinner(
                            "Workout wird nach deinen Änderungen neu analysiert ..."
                        ):
                            try:
                                (
                                    deterministic_analysis,
                                    workout_interpretation,
                                ) = analyze_workout(
                                    parsed_workout=current_workout,
                                    sportart=sportart,
                                    api_key=MISTRAL_API_KEY,
                                    model=MISTRAL_TEXT_MODEL,
                                )
                            except (RuntimeError, ValueError) as exc:
                                st.error(
                                    "Die geänderte Workout-Version konnte "
                                    f"nicht analysiert werden: {exc}"
                                )
                            else:
                                st.session_state[
                                    "deterministic_analysis"
                                ] = deterministic_analysis
                                st.session_state[
                                    "workout_interpretation"
                                ] = workout_interpretation
                                st.session_state["save_notice"] = {
                                    "type": "success",
                                    "text": (
                                        "Workout-Änderungen wurden übernommen "
                                        "und neu analysiert."
                                    ),
                                }
                                st.rerun()

                st.markdown("---")
                st.subheader(
                    "Wie hat es sich angefühlt?"
                )

                duration_minutes = (
                    st.number_input(
                        "Trainingsdauer in Minuten",
                        min_value=1,
                        max_value=600,
                        value=int(
                            st.session_state[
                                "trainingsdauer"
                            ]
                        ),
                        step=5,
                    )
                )

                st.session_state[
                    "trainingsdauer"
                ] = int(duration_minutes)

                rpe = st.slider(
                    "Wie anstrengend war das Workout? "
                    "RPE 1–10",
                    min_value=1,
                    max_value=10,
                    value=int(
                        st.session_state[
                            "aktuelles_rpe"
                        ]
                    ),
                )

                st.session_state[
                    "aktuelles_rpe"
                ] = int(rpe)

                workout_comment = (
                    st.text_area(
                        "Kommentar zum Workout "
                        "oder zur Tagesform",
                        value=(
                            st.session_state[
                                "workout_kommentar"
                            ]
                        ),
                        placeholder=(
                            "z. B. Beine waren ab Runde 3 "
                            "schwer, Puls ungewöhnlich hoch "
                            "oder sehr gute Tagesform"
                        ),
                    )
                )

                st.session_state[
                    "workout_kommentar"
                ] = workout_comment.strip()

                st.markdown("---")
                st.subheader("💾 Training dauerhaft sichern")

                save_notice = st.session_state.get("save_notice")
                if save_notice:
                    notice_type = save_notice.get("type", "info")
                    notice_text = save_notice.get("text", "")

                    if notice_type == "success":
                        st.success(notice_text)
                    elif notice_type == "warning":
                        st.warning(notice_text)
                    elif notice_type == "error":
                        st.error(notice_text)
                    else:
                        st.info(notice_text)

                    st.session_state["save_notice"] = None

                if conn is None:
                    st.warning(
                        "Google Sheets ist derzeit nicht verbunden."
                    )
                    if gsheets_error:
                        st.caption(gsheets_error)

                if st.button(
                    "🚀 Workout in Google Sheets speichern",
                    disabled=conn is None,
                    type="primary",
                    width="stretch",
                    key="save_workout_tab1",
                ):
                    st.session_state["pending_save"] = True

                st.caption(
                    "Beim Speichern werden Workout, Belastungsdaten, "
                    "Trainingsklassifikation und Coach-Feedback übernommen."
                )

                if st.button(
                    "🗑️ Aktuelles Workout zurücksetzen",
                    width="stretch",
                ):
                    reset_current_workout()
                    st.rerun()



# ============================================================
# MEIN COACH · EINORDNUNG
# ============================================================

with tab2:
    st.subheader(
        "📊 Trainingsanalyse und Belastung"
    )

    # Immer aus Session State lesen. History-Kontext wird beim Athletenladen
    # bereits aus den gespeicherten Analyse-JSONs rekonstruiert.
    parsed_workout = st.session_state.get(
        "parsed_workout"
    )

    deterministic_analysis = st.session_state.get(
        "deterministic_analysis"
    )

    workout_interpretation = st.session_state.get(
        "workout_interpretation"
    )

    if (
        deterministic_analysis is None
        or workout_interpretation is None
    ):
        athlete_for_coach = st.session_state.get("athleten_name", "").strip()
        if not athlete_for_coach:
            st.info("Wähle im Status zuerst dein Athletenprofil aus.")
        else:
            st.info(
                "Für dieses Profil ist noch keine auswertbare Einheit vorhanden. "
                "Speichere ein Workout, dann aktualisiert sich dein Coach automatisch."
            )

    else:
        user_name = (
            st.session_state.get(
                "athleten_name",
                "Unbekannt",
            ).strip()
            or "Unbekannt"
        )

        user_sport = (
            st.session_state.get(
                "sportart",
                "Nicht angegeben",
            )
        )

        user_level = (
            st.session_state.get(
                "athleten_level",
                "Fortgeschritten (Intermediate)",
            )
        )

        user_injuries = (
            st.session_state.get(
                "verletzungen",
                "",
            ).strip()
        )

        user_comment = (
            st.session_state.get(
                "workout_kommentar",
                "",
            ).strip()
        )

        user_rpe = int(
            st.session_state.get(
                "aktuelles_rpe",
                7,
            )
        )

        duration_minutes = int(
            st.session_state.get(
                "trainingsdauer",
                60,
            )
        )

        if parsed_workout is not None:
            structural_score = calculate_structural_score(parsed_workout)
            total_score = calculate_load_score(
                structural_score=structural_score,
                rpe=user_rpe,
                duration_minutes=duration_minutes,
                level=user_level,
            )
        else:
            # History-Kontext: Score wurde bereits beim Speichern berechnet.
            structural_score = 0
            cached_history = _filter_cached_history(
                st.session_state.get("history_cache"), user_name, days=90
            )
            latest_saved = sort_training_history(cached_history).iloc[0] if not cached_history.empty else {}
            total_score = safely_convert_to_int(
                latest_saved.get("score") if hasattr(latest_saved, "get") else 0,
                default=0,
            )

        level_factor = (
            get_level_factor(
                user_level
            )
        )

        (
            status_text,
            status_type,
        ) = get_load_status(
            total_score
        )

        if parsed_workout is not None:
            current_workout_text = format_workout_as_text(parsed_workout)
        else:
            cached_history = _filter_cached_history(
                st.session_state.get("history_cache"), user_name, days=90
            )
            latest_saved = sort_training_history(cached_history).iloc[0] if not cached_history.empty else {}
            current_workout_text = str(
                latest_saved.get("workout", "") if hasattr(latest_saved, "get") else ""
            ).strip()

        # ----------------------------------------------------
        # HISTORIE LADEN
        # ----------------------------------------------------

        try:
            training_history = _filter_cached_history(
                st.session_state.get("history_cache"), user_name, days=90
            )
            training_history = normalize_training_dates(
                training_history
            )

        except Exception as exc:
            training_history = pd.DataFrame(
                columns=SHEET_COLUMNS
            )

            st.warning(
                "Die Trainingshistorie konnte "
                "nicht vollständig geladen werden: "
                f"{exc}"
            )

        if (
            st.session_state.get(
                "letzter_save_key"
            )
            is not None
        ):
            training_history = (
                remove_current_workout_from_history(
                    training_history,
                    current_workout_text=(
                        current_workout_text
                    ),
                    current_rpe=user_rpe,
                )
            )

        history_summary = build_history_summary(
            training_history,
            period_days=28,
        )

        trend_analysis = build_trends(
            training_history
        )

        training_balance = build_training_balance(
            trend_analysis,
            primary_goal=user_sport,
        )

        training_analysis = analyze_history(
            history_summary=history_summary,
        )

        st.session_state[
            "letzte_trainingsanalyse"
        ] = training_analysis

        # ----------------------------------------------------
        # REGELBASIERTE COACH-GRUNDLAGE
        # ----------------------------------------------------

        readiness = training_analysis.readiness
        weekly_focus = training_analysis.weekly_focus
        positive_observations = (
            training_analysis.positive_observations
        )

        # ----------------------------------------------------
        # KI-COACH EINMALIG ERZEUGEN
        # ----------------------------------------------------

        coach_state_key = create_stable_hash(
            {
                "name": user_name,
                "sportart": user_sport,
                "level": user_level,
                "injuries": user_injuries,
                "history_summary": history_summary,
                "training_analysis": training_analysis,
                "readiness": readiness,
                "weekly_focus": weekly_focus,
                "positive_observations": positive_observations,
            }
        )

        if (
            st.session_state.get("letzter_state_key")
            != coach_state_key
        ):
            with st.spinner(
                "Coach analysiert aktuelles Training "
                "und Trainingshistorie ..."
            ):


                # --------------------------------------------
                # AUSFÜHRLICHE COACH-EINORDNUNG
                # --------------------------------------------

                try:
                    coach_result = build_coach_feedback(
                        training_analysis=training_analysis,
                        readiness=readiness,
                        weekly_focus=weekly_focus,
                        positive_observations=positive_observations,
                        history_summary=history_summary,
                        sportart=user_sport,
                        level=user_level,
                        injuries=user_injuries,
                        api_key=MISTRAL_API_KEY,
                        model=MISTRAL_TEXT_MODEL,
                    )

                    coach_text = coach_result.get(
                        "coach_feedback",
                        "",
                    )

                    readiness_summary = coach_result.get(
                        "readiness_summary",
                        "",
                    )

                except RuntimeError as exc:
                    print(
                        f"Coach-Feedback fehlgeschlagen: {exc}"
                    )

                    coach_text = (
                        "Mit weiteren gespeicherten Einheiten "
                        "kann ich dein Training und seine "
                        "Entwicklung zuverlässiger einordnen."
                    )

                    readiness_summary = ""

                # --------------------------------------------
                # DAILY COACH TIPS
                # --------------------------------------------

                try:
                    daily_coach_tips = build_daily_tips(
                        readiness=readiness,
                        weekly_focus=weekly_focus,
                        training_analysis=training_analysis,
                        history_summary=history_summary,
                        sportart=user_sport,
                        level=user_level,
                        workout_rpe=user_rpe,
                        duration_minutes=duration_minutes,
                        injuries=user_injuries,
                        api_key=MISTRAL_API_KEY,
                        model=MISTRAL_TEXT_MODEL,
                    )

                except RuntimeError as exc:
                    print(
                        f"Daily Coach Tips fehlgeschlagen: {exc}"
                    )

                    daily_coach_tips = {
                        "training": (
                            readiness.get("plan_guidance")
                            or (
                                "Folge grundsätzlich deinem "
                                "bestehenden Trainingsplan."
                            )
                        ),
                        "nutrition": (
                            "Versorge dich passend zu deiner "
                            "Trainingsbelastung mit ausreichend "
                            "Flüssigkeit und Energie."
                        ),
                        "recovery": (
                            "Plane normale Erholung passend zu "
                            "deiner aktuellen Belastbarkeit ein."
                        ),
                    }

                # --------------------------------------------
                # ERGEBNISSE CACHEN
                # --------------------------------------------

                st.session_state[
                    "letzter_coach_text"
                ] = coach_text

                st.session_state[
                    "letzte_daily_coach_tips"
                ] = daily_coach_tips

                st.session_state[
                    "letzter_state_key"
                ] = coach_state_key

                st.session_state[
                    "letzte_readiness_summary"
                ] = readiness_summary


        # ----------------------------------------------------
        # COACH-DATEN AUS SESSION STATE
        # ----------------------------------------------------

        coach_display_text = (
            st.session_state.get(
                "letzter_coach_text"
            )
            or (
                "Noch kein Coach-Feedback verfügbar."
            )
        )

        coach_text = st.session_state.get(
            "letzter_coach_text",
            "",
        )

        readiness_summary = st.session_state.get(
            "letzte_readiness_summary",
            "",
        )

        daily_coach_tips = st.session_state.get(
            "letzte_daily_coach_tips",
            {},
        )

        daily_coach_tips = (
            st.session_state.get(
                "letzte_daily_coach_tips"
            )
            or {
                "training": (
                    "Noch kein Trainingstipp verfügbar."
                ),
                "nutrition": (
                    "Noch kein Ernährungstipp verfügbar."
                ),
                "recovery": (
                    "Noch kein Recovery-Tipp verfügbar."
                ),
            }
        )

        # ----------------------------------------------------
        # ANGEFORDERTES SPEICHERN AUS TAB 1 VERARBEITEN
        # ----------------------------------------------------

        if st.session_state.get("pending_save"):
            save_payload = {
                "name": user_name,
                "sportart": user_sport,
                "level": user_level,
                "duration_minutes": duration_minutes,
                "rpe": user_rpe,
                "score": total_score,
                "workout": current_workout_text,
                "injuries": user_injuries,
                "comment": user_comment,
                "deterministic_analysis": deterministic_analysis,
            }

            current_save_key = create_stable_hash(save_payload)
            already_saved = (
                st.session_state.get("letzter_save_key")
                == current_save_key
            )

            if already_saved:
                st.session_state["save_notice"] = {
                    "type": "info",
                    "text": (
                        "Dieses Workout wurde in der aktuellen Sitzung "
                        "bereits gespeichert."
                    ),
                }
            elif conn is None:
                st.session_state["save_notice"] = {
                    "type": "warning",
                    "text": "Google Sheets ist derzeit nicht verbunden.",
                }
            else:
                timestamp = datetime.now(APP_TIMEZONE).isoformat(
                    timespec="seconds"
                )

                new_entry = pd.DataFrame(
                    [
                        {
                            "zeitstempel": timestamp,
                            "name": user_name,
                            "sportart": user_sport,
                            "level": user_level,
                            "dauer_minuten": duration_minutes,
                            "rpe": user_rpe,
                            "score": total_score,
                            "workout": current_workout_text,
                            "verletzungen": user_injuries,
                            "kommentar": user_comment,
                            "coach_feedback": str(coach_display_text).strip(),
                            "bewegungsmuster_json": json_dumps_for_sheet(
                                normalize_movement_patterns(
                                    deterministic_analysis.bewegungsmuster
                                )
                            ),
                            "muskelgruppen_json": json_dumps_for_sheet(
                                normalize_muscle_groups(
                                    deterministic_analysis.muskelgruppen
                                )
                            ),
                            "trainingsziele_json": json_dumps_for_sheet(
                                deterministic_analysis.trainingsziele
                            ),
                            "belastungsarten_json": json_dumps_for_sheet(
                                deterministic_analysis.belastungsarten
                            ),
                            "trainingsvolumen_json": json_dumps_for_sheet(
                                asdict(deterministic_analysis.trainingsvolumen)
                            ),
                            "klassifikation_json": json_dumps_for_sheet(
                                workout_interpretation.klassifikation
                            ),
                            "crossfit_movements_json": json_dumps_for_sheet(
                                deterministic_analysis.movements
                            ),
                        }
                    ],
                    columns=SHEET_COLUMNS,
                )

                try:
                    existing_data = st.session_state.get("history_cache")

                    if existing_data is None:
                        existing_data = pd.DataFrame(
                            columns=SHEET_COLUMNS
                        )

                    append_workout_history(
                        conn=conn,
                        spreadsheet_url=SHEET_URL,
                        worksheet_name=WORKSHEET_NAME,
                        dataframe=new_entry,
                        columns=SHEET_COLUMNS,
                    )

                    updated_data = pd.concat(
                        [existing_data, new_entry],
                        ignore_index=True,
                    )
                except Exception as exc:
                    st.session_state["save_notice"] = {
                        "type": "error",
                        "text": (
                            "Das Workout konnte nicht gespeichert werden: "
                            f"{exc}"
                        ),
                    }
                else:
                    st.session_state["letzter_save_key"] = current_save_key
                    # Cache lokal mit dem gerade erfolgreich geschriebenen Stand aktualisieren.
                    # Dadurch ist nach dem Speichern kein zusätzlicher Sheets-Read nötig.
                    st.session_state["history_cache"] = updated_data.copy()
                    st.session_state["history_cache_athlete"] = user_name.strip().casefold()
                    # Erzwingt nach dem Speichern ein Neuladen des Coach-Kontexts
                    # aus der aktualisierten Historie.
                    st.session_state["coach_context_key"] = None
                    st.session_state["coach_context_source"] = None
                    st.session_state["workout_entry_requested"] = False
                    st.session_state["save_notice"] = {
                        "type": "success",
                        "text": (
                            f"Workout für {user_name} wurde erfolgreich "
                            "gespeichert."
                        ),
                    }

            st.session_state["pending_save"] = False
            st.rerun()

        # ----------------------------------------------------
        # DASHBOARD
        # ----------------------------------------------------

        trend_windows = trend_analysis.get(
            "windows",
            {},
        )

        window_7 = trend_windows.get(
            "7_days",
            {},
        )
        window_14 = trend_windows.get(
            "14_days",
            {},
        )
        window_28 = trend_windows.get(
            "28_days",
            {},
        )

        sessions_7 = int(
            window_7.get(
                "sessions",
                0,
            )
            or 0
        )
        sessions_14 = int(
            window_14.get(
                "sessions",
                0,
            )
            or 0
        )
        sessions_28 = int(
            window_28.get(
                "sessions",
                0,
            )
            or 0
        )

        load_7 = float(
            window_7.get(
                "total_load",
                0,
            )
            or 0
        )
        load_14 = float(
            window_14.get(
                "total_load",
                0,
            )
            or 0
        )
        load_28 = float(
            window_28.get(
                "total_load",
                0,
            )
            or 0
        )

        average_rpe_7 = float(
            window_7.get(
                "average_rpe",
                0,
            )
            or 0
        )
        average_rpe_14 = float(
            window_14.get(
                "average_rpe",
                0,
            )
            or 0
        )
        average_rpe_28 = float(
            window_28.get(
                "average_rpe",
                0,
            )
            or 0
        )

        trend_block = trend_analysis.get(
            "trends",
            {},
        )
        load_trend = trend_block.get(
            "load",
            {},
        )
        frequency_trend = trend_block.get(
            "frequency",
            {},
        )
        rpe_trend = trend_block.get(
            "rpe",
            {},
        )
        goal_trends = trend_block.get(
            "training_goals",
            [],
        )
        movement_trends = trend_block.get(
            "movement_patterns",
            [],
        )

        diversity = trend_analysis.get(
            "diversity",
            {},
        )
        consistency = trend_analysis.get(
            "consistency",
            {},
        )

        balance_overview = training_balance.get(
            "overview",
            {},
        )
        balance_findings = training_balance.get(
            "findings",
            [],
        )

        analysis_overview = (
            training_analysis.overview or {}
        )

        finding_count = int(
            analysis_overview.get(
                "finding_count",
                len(training_analysis.top_findings),
            )
            or 0
        )

        st.session_state["status_dashboard_data"] = {
            "sessions_28": sessions_28,
            "load_trend": load_trend,
            "consistency": consistency,
            "diversity": diversity,
        }

        render_coach_dashboard(
            user_name=user_name,
            user_sport=user_sport,
            user_level=user_level,
            sessions_28=sessions_28,
            readiness=readiness,
            positive_observations=positive_observations,
            weekly_focus=weekly_focus,
            coach_text=coach_display_text,
            daily_coach_tips=daily_coach_tips,
            load_trend=load_trend,
            consistency=consistency,
            diversity=diversity,
        )




# ============================================================
# TRAINING · HISTORIE
# ============================================================

with tab3:
    st.subheader(
        "🏋️ Training"
    )
    st.caption("Letzte Einheiten und gespeicherte Trainingshistorie")

    search_name = (
        st.session_state.get(
            "athleten_name",
            "",
        ).strip()
    )

    if not search_name:
        st.info(
            "Trage im ersten Tab deinen "
            "Namen ein, um deine "
            "Trainingshistorie zu laden."
        )

    elif conn is None:
        st.error(
            "Die Historie kann nicht geladen "
            "werden, weil Google Sheets nicht "
            "verbunden ist."
        )

        if gsheets_error:
            st.caption(
                gsheets_error
            )

    else:
        try:
            history_df = st.session_state.get("history_cache")
            if history_df is None:
                history_df = pd.DataFrame(columns=SHEET_COLUMNS)

        except Exception as exc:
            st.error(
                "Fehler beim Laden der Historie: "
                f"{exc}"
            )

        else:
            normalized_names = (
                history_df["name"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.casefold()
            )

            user_history = (
                history_df[
                    normalized_names
                    == search_name.casefold()
                ].copy()
            )

            if user_history.empty:
                st.info(
                    f"Für „{search_name}“ wurden "
                    "noch keine gespeicherten "
                    "Workouts gefunden."
                )

            else:
                user_history[
                    "zeitstempel_sort"
                ] = pd.to_datetime(
                    user_history[
                        "zeitstempel"
                    ],
                    errors="coerce",
                    utc=True,
                )

                user_history = (
                    user_history.sort_values(
                        by=(
                            "zeitstempel_sort"
                        ),
                        ascending=False,
                        na_position="last",
                    )
                )

                st.write(
                    "**Gespeicherte Workouts:** "
                    f"{len(user_history)}"
                )

                table_history = user_history.copy()
                
                table_history[
                    "Dauer"
                ] = pd.to_numeric(
                    table_history[
                        "dauer_minuten"
                    ],
                    errors="coerce",
                )

                table_history[
                    "RPE"
                ] = pd.to_numeric(
                    table_history[
                        "rpe"
                    ],
                    errors="coerce",
                )

                table_history[
                    "Load"
                ] = pd.to_numeric(
                    table_history[
                        "score"
                    ],
                    errors="coerce",
                )

                # -----------------------------------------
                # Historie für Anzeige vorbereiten
                # -----------------------------------------
                                                           
                history_display = sort_training_history(
                    table_history
                )

                history_display = format_training_dates(
                    history_display,
                    include_time=False,
                )
 
                st.dataframe(
                    history_display[
                        [
                            "zeitstempel",
                            "workout",
                            "Dauer",
                            "RPE",
                            "Load",
                        ]
                    ].head(10),
                    column_config={
                        "workout": "Workout",
                        "Dauer": st.column_config.NumberColumn(
                            "Dauer",
                            format="%d Min.",
                        ),
                        "RPE": st.column_config.NumberColumn(
                            "RPE",
                            format="%.0f",
                        ),
                        "Load": st.column_config.NumberColumn(
                            "Load",
                            format="%.0f",
                        ),
                    },
                    hide_index=True,
                    width="stretch",
                )

                st.markdown("#### Workout-Details")

                for _, row in (
                    user_history.iterrows()
                ):
                    raw_timestamp = row.get(
                        "zeitstempel",
                        "",
                    )

                    parsed_timestamp = (
                        pd.to_datetime(
                            raw_timestamp,
                            errors="coerce",
                            utc=True,
                        )
                    )

                    if pd.notna(
                        parsed_timestamp
                    ):
                        try:
                            local_timestamp = (
                                parsed_timestamp
                                .tz_convert(
                                    APP_TIMEZONE_NAME
                                )
                            )

                            displayed_date = (
                                local_timestamp
                                .strftime(
                                    "%d.%m.%Y %H:%M"
                                )
                            )

                        except Exception:
                            displayed_date = (
                                parsed_timestamp
                                .strftime(
                                    "%d.%m.%Y %H:%M"
                                )
                            )

                    else:
                        displayed_date = (
                            str(
                                raw_timestamp
                            ).strip()
                            or "Unbekanntes Datum"
                        )

                    score = (
                        safely_convert_to_int(
                            row.get(
                                "score"
                            ),
                            default=0,
                        )
                    )

                    rpe_value = (
                        safely_convert_to_int(
                            row.get(
                                "rpe"
                            ),
                            default=0,
                        )
                    )

                    duration_value = (
                        safely_convert_to_int(
                            row.get(
                                "dauer_minuten"
                            ),
                            default=0,
                        )
                    )

                    sport = str(
                        row.get(
                            "sportart",
                            "Sport",
                        )
                    ).strip()

                    if score <= 450:
                        score_icon = "🟢"

                    elif score <= 750:
                        score_icon = "🟡"

                    else:
                        score_icon = "🔴"

                    expander_title = (
                        f"{score_icon} "
                        f"{displayed_date} – "
                        f"{sport} | "
                        f"Score: {score}"
                    )

                    with st.expander(
                        expander_title
                    ):
                        st.write(
                            "**Level:** "
                            f"{row.get('level', '')}"
                        )

                        st.write(
                            f"**Dauer:** "
                            f"{duration_value} Minuten | "
                            f"**RPE:** {rpe_value}/10"
                        )

                        injury_value = (
                            row.get(
                                "verletzungen"
                            )
                        )

                        if (
                            pd.notna(
                                injury_value
                            )
                            and str(
                                injury_value
                            ).strip()
                        ):
                            st.warning(
                                "⚠️ **Einschränkungen:** "
                                f"{injury_value}"
                            )

                        comment_value = (
                            row.get(
                                "kommentar"
                            )
                        )

                        if (
                            pd.notna(
                                comment_value
                            )
                            and str(
                                comment_value
                            ).strip()
                        ):
                            st.info(
                                "💬 **Tagesform:** "
                                f"{comment_value}"
                            )

                        st.write(
                            "**Absolviertes Training:**"
                        )

                        workout_value = row.get(
                            "workout",
                            "",
                        )

                        workout_parts = str(
                            workout_value
                        ).split(" | ")

                        for workout_part in (
                            workout_parts
                        ):
                            workout_part = (
                                workout_part.strip()
                            )

                            if workout_part:
                                st.markdown(
                                    f"- {workout_part}"
                                )

                        coach_value = row.get(
                            "coach_feedback"
                        )

                        if (
                            pd.notna(
                                coach_value
                            )
                            and str(
                                coach_value
                            ).strip()
                        ):
                            st.write(
                                "**Gespeichertes "
                                "Coach-Feedback:**"
                            )

                            st.write(
                                coach_value
                            )


# ============================================================
# MEIN COACH · ANALYSE
# ============================================================

with tab4:
    # ----------------------------------------------------
    # ANALYSE-DATEN DIREKT AUS DER GESPEICHERTEN HISTORIE
    # ----------------------------------------------------
    #
    # Der Analyse-Tab darf nicht davon abhängen, ob Variablen zuvor in
    # einem anderen Tab erzeugt wurden. Streamlit führt zwar das Skript
    # komplett aus, aber einzelne Codepfade können übersprungen werden.
    # Deshalb werden Trends und Trainingsbalance hier lokal aufgebaut.
    analysis_user_name = st.session_state.get("athleten_name", "").strip()
    analysis_user_sport = st.session_state.get("sportart", "")

    analysis_history = _filter_cached_history(
        st.session_state.get("history_cache"),
        analysis_user_name,
        days=90,
    )

    analysis_trend_analysis = build_trends(analysis_history)
    training_balance = build_training_balance(
        analysis_trend_analysis,
        primary_goal=analysis_user_sport,
    )

    analysis_trend_block = analysis_trend_analysis.get("trends", {})
    load_trend = analysis_trend_block.get("load", {})
    frequency_trend = analysis_trend_block.get("frequency", {})
    rpe_trend = analysis_trend_block.get("rpe", {})

    analysis_readiness = st.session_state.get("status_readiness")
    if isinstance(analysis_readiness, dict) and analysis_readiness:
        render_readiness_card(analysis_readiness)

        # ----------------------------------------------------
        # ENTWICKLUNG
        # ----------------------------------------------------

        st.markdown("### Entwicklung")
        st.caption(
            "Vergleich der letzten 14 Tage mit den vorherigen 14 Tagen. "
            "Der Belastungsverlauf darunter zeigt die letzten 28 Tage."
        )

        trend_col1, trend_col2, trend_col3 = st.columns(3)

        trend_col1.metric(
            "Belastung",
            load_trend.get("text", "Noch nicht bewertbar"),
            (
                f"{load_trend.get('change_percent'):+.1f} %"
                if load_trend.get("change_percent") is not None
                else None
            ),
        )

        trend_col2.metric(
            "Trainingshäufigkeit",
            frequency_trend.get("text", "Noch nicht bewertbar"),
            f"{frequency_trend.get('current_sessions', 0)} Einheiten",
        )

        trend_col3.metric(
            "Intensität",
            rpe_trend.get("text", "Noch nicht bewertbar"),
            (
                f"Ø RPE {rpe_trend.get('current_value', 0):.1f}"
                if float(rpe_trend.get("current_value", 0) or 0) > 0
                else None
            ),
        )


    st.subheader("Analyse deiner letzten 28 Tage")
    st.caption(
        "So verteilt sich dein Training über Bewegungsmuster, Muskelgruppen, "
        "Trainingsziele und Belastungsarten."
    )

    # Die 28-Tage-Analyse basiert auf der gespeicherten Historie.
    # Ein neu eingegebenes Workout ist dafür nicht erforderlich.
    analysis_history_available = (
        not analysis_history.empty
        and isinstance(training_balance, dict)
        and bool(training_balance)
    )

    if not analysis_history_available:
        st.info(
            "Für dieses Profil ist noch keine auswertbare Trainingshistorie vorhanden."
        )

    else:
        # ----------------------------------------------------
        # VISUELLE 28-TAGE-ANALYSE
        # ----------------------------------------------------

        movement_items = [
            item for item in training_balance.get("movement_patterns", [])
            if float(item.get("share_percent", 0) or 0) > 0
        ]
        muscle_items = [
            item for item in training_balance.get("muscle_groups", [])
            if float(item.get("share_percent", 0) or 0) > 0
        ]
        goal_items = [
            item for item in training_balance.get("training_goals", [])
            if float(item.get("share_percent", 0) or 0) > 0
        ]
        load_items = [
            item for item in training_balance.get("load_types", [])
            if float(item.get("share_percent", 0) or 0) > 0
        ]

        chart_left, chart_right = st.columns([1.15, 1], gap="large")

        with chart_left:
            st.markdown("#### Bewegungsmuster")
            if movement_items:
                movement_chart = pd.DataFrame([
                    {
                        "Bewegungsmuster": str(item.get("label", "–")),
                        "Anteil": float(item.get("share_percent", 0) or 0),
                    }
                    for item in movement_items
                ])
                donut_spec = {
                    "mark": {"type": "arc", "innerRadius": 40, "outerRadius": 95},
                    "encoding": {
                        "theta": {"field": "Anteil", "type": "quantitative", "stack": True},
                        "color": {
                            "field": "Bewegungsmuster",
                            "type": "nominal",
                            "legend": {"orient": "bottom", "title": None, "columns": 4},
                        },
                        "tooltip": [
                            {"field": "Bewegungsmuster", "type": "nominal"},
                            {"field": "Anteil", "type": "quantitative", "format": ".1f", "title": "Anteil %"},
                        ],
                    },
                    "view": {"stroke": None},
                    "height": 340,
                }
                st.vega_lite_chart(movement_chart, donut_spec, width="stretch")
                with st.expander("Details anzeigen", expanded=False):
                    render_balance_dimension("Bewegungsmuster · Details", training_balance.get("movement_patterns", []), max_rows=11)
            else:
                st.info("Noch keine Bewegungsmuster für die letzten 28 Tage verfügbar.")

        with chart_right:
            st.markdown("#### Muskelgruppen")
            if muscle_items:
                muscle_chart = (
                    pd.DataFrame([
                        {
                            "Muskelgruppe": str(item.get("label", "–")),
                            "Anteil": float(item.get("share_percent", 0) or 0),
                        }
                        for item in muscle_items
                    ])
                    .sort_values("Anteil", ascending=True)
                    .set_index("Muskelgruppe")
                )
                st.bar_chart(muscle_chart, horizontal=True, width="stretch")
                with st.expander("Details anzeigen", expanded=False):
                    render_balance_dimension("Muskelgruppen · Details", training_balance.get("muscle_groups", []), max_rows=12)
            else:
                st.info("Noch keine Muskelgruppenverteilung verfügbar.")

        visual_left, visual_right = st.columns(2, gap="large")
        with visual_left:
            st.markdown("#### Trainingsziele")
            if goal_items:
                goal_chart = (
                    pd.DataFrame([
                        {
                            "Trainingsziel": str(item.get("label", "–")),
                            "Anteil": float(item.get("share_percent", 0) or 0),
                        }
                        for item in goal_items[:8]
                    ])
                    .sort_values("Anteil", ascending=True)
                    .set_index("Trainingsziel")
                )
                st.bar_chart(goal_chart, horizontal=True, width="stretch")
                with st.expander("Details anzeigen", expanded=False):
                    render_balance_dimension("Trainingsziele · Details", training_balance.get("training_goals", []), max_rows=12)
            else:
                st.info("Noch keine Trainingsziel-Verteilung verfügbar.")

        with visual_right:
            st.markdown("#### Belastungsarten")
            if load_items:
                load_chart = (
                    pd.DataFrame([
                        {
                            "Belastungsart": str(item.get("label", "–")),
                            "Anteil": float(item.get("share_percent", 0) or 0),
                        }
                        for item in load_items[:8]
                    ])
                    .sort_values("Anteil", ascending=True)
                    .set_index("Belastungsart")
                )
                st.bar_chart(load_chart, horizontal=True, width="stretch")
                with st.expander("Details anzeigen", expanded=False):
                    render_balance_dimension("Belastungsarten · Details", training_balance.get("load_types", []), max_rows=10)
            else:
                st.info("Noch keine Belastungsarten-Verteilung verfügbar.")

        # ----------------------------------------------------
        # AUFFÄLLIGKEITEN
        # ----------------------------------------------------

        # st.markdown("### Auffälligkeiten")
        # st.caption(
        #     "Hier erscheinen nur relevante Abweichungen im aktuellen "
        #     "Trainingsmix. Die vollständigen Einzelwerte findest du über "
        #     "‚Details anzeigen‘ direkt an den Grafiken."
        # )

        # if balance_findings:
        #     finding_columns = st.columns(2, gap="large")
        #     for index, finding in enumerate(balance_findings[:6]):
        #         with finding_columns[index % 2]:
        #             st.markdown(
        #                 f"""
        #                 <div class="finding-card">
        #                     <div class="muted-label">TRAININGSBALANCE</div>
        #                     <strong>{html.escape(str(finding.get('title', 'Hinweis')))}</strong>
        #                     <div>{html.escape(str(finding.get('text', '')))}</div>
        #                 </div>
        #                 """,
        #                 unsafe_allow_html=True,
        #             )
        # else:
        #     st.success(
        #         "Die erfassten Trainingsbestandteile liegen aktuell "
        #         "innerhalb der hinterlegten Zielkorridore."
        #     )

        # ----------------------------------------------------
        # CROSSFIT SKILLS
        # Nur für CrossFit-Athleten, dort immer sichtbar
        # ----------------------------------------------------

        if str(analysis_user_sport).strip().casefold() == "crossfit":
            crossfit_items = training_balance.get(
                "crossfit_movements",
                [],
            )

          #  st.markdown("### CrossFit Skills")

            render_crossfit_movements(
                crossfit_items,
                max_rows=15,
            )


        # trend_detail_left, trend_detail_right = st.columns(2, gap="large")

        # with trend_detail_left:
        #     st.markdown("##### Trainingsziele")
        #     if goal_trends:
        #         for item in goal_trends[:4]:
        #             st.write(f"{item.get('symbol', '•')} {item.get('text', '')}")
        #     else:
        #         st.caption("Noch keine klaren Veränderungen bei den Trainingszielen.")

        # with trend_detail_right:
        #     st.markdown("##### Bewegungsmuster")
        #     if movement_trends:
        #         for item in movement_trends[:4]:
        #             st.write(f"{item.get('symbol', '•')} {item.get('text', '')}")
        #     else:
        #         st.caption("Noch keine klaren Veränderungen bei den Bewegungsmustern.")

        # st.markdown("#### Belastungsverlauf · 28 Tage")

        # chart_history = training_history.copy()
        # if not chart_history.empty:
        #     timestamp_column = (
        #         "zeitstempel_parsed"
        #         if "zeitstempel_parsed" in chart_history.columns
        #         else "zeitstempel"
        #     )
        #     chart_history["dashboard_date"] = pd.to_datetime(
        #         chart_history[timestamp_column], errors="coerce", utc=True
        #     )
        #     chart_history["dashboard_score"] = pd.to_numeric(
        #         chart_history.get("score", 0), errors="coerce"
        #     ).fillna(0)

        #     daily_load = (
        #         chart_history
        #         .dropna(subset=["dashboard_date"])
        #         .assign(dashboard_date=lambda frame: frame["dashboard_date"].dt.date)
        #         .groupby("dashboard_date", as_index=False)["dashboard_score"]
        #         .sum()
        #         .rename(columns={
        #             "dashboard_date": "zeitstempel",
        #             "dashboard_score": "Belastung",
        #         })
        #         .set_index("zeitstempel")
        #     )

        #     if not daily_load.empty:
        #         st.line_chart(daily_load, width="stretch")
        #     else:
        #         st.info("Für den Belastungstrend fehlen gültige Datumswerte.")
        # else:
        #     st.info(
        #         "Der Belastungstrend erscheint nach dem ersten gespeicherten Workout."
        #     )