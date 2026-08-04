import base64
import html
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


from services.analysis import build_findings
from services.date_utils import (
    normalize_training_dates,
    format_training_dates,
)
from services.trends import build_trends
from services.training_balance import build_training_balance

from services.coach import (
    create_coach_state_key,
    get_coach_feedback,
    classify_workout,
)
from services.coach_logic import (
    build_readiness_summary,
    build_weekly_focus,
    build_positive_observations,
)
from services.date_utils import (
    normalize_training_dates,
    format_training_dates,
    sort_training_history,
)
from ui.coach_dashboard import render_coach_dashboard
from ui.crossfit_dashboard import render_crossfit_dashboard

from services.history import (
    build_history_summary,
    get_user_training_history,
    remove_current_workout_from_history,
)
from services.mistral_service import (
    call_mistral,
    parse_workout_response,
)
from services.scoring import (
    calculate_load_score,
    calculate_structural_score,
    get_level_factor,
    get_load_status,
    calculate_classification_dimensions,
)
from services.sheets import (
    read_workout_history,
    write_workout_history,
)
from services.utils import (
    create_stable_hash,
    format_workout_as_text,
    json_dumps_for_sheet,
    safely_convert_to_int,
)

from ui.coach_dashboard import render_coach_dashboard
from ui.theme import apply_theme


# ============================================================
# APP-KONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EU Sport KI Coach",
    page_icon="🇪🇺",
    layout="wide",
)
apply_theme()

st.title("🇪🇺 KI Sportcoach")
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
    "letzter_state_key": None,
    "letzter_save_key": None,
    "letzte_trainingsanalyse": None,
    "pending_save": False,
    "save_notice": None,
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
            "Erlaubt sind CrossFit, Hyrox, "
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
# PROMPT FÜR WORKOUT-ERKENNUNG
# ============================================================

WORKOUT_EXTRACTION_PROMPT = """
Du bist der präzise Daten-Assistent einer Sport-App für
CrossFit, Hyrox und Laufen.

Analysiere die bereitgestellten Workout-Daten exakt.

STRUKTURREGELN:

1. Kraftteile oder klar getrennte Einzelübungen, zum Beispiel
   Deadlifts oder Squats, kommen als jeweils eigenes Objekt
   in die Liste.

2. Zusammengehörige komplexe Workouts wie AMRAP, RFT, EMOM,
   Chipper oder For Time dürfen nicht in unabhängige
   Einzelübungen zerlegt werden.

3. Erstelle für ein komplexes Workout genau ein Objekt.
   Verwende als Namen beispielsweise:
   "AMRAP 20", "5 RFT", "EMOM 12" oder "For Time".

4. Führe die enthaltenen Übungen, Wiederholungen, Distanzen,
   Gewichte und Zeitlimits vollständig im Feld "details" auf.

5. Erfinde keine Gewichte, Wiederholungen oder Übungen.

Antworte ausschließlich als gültiges JSON in diesem Format:

{
  "workout_erkannt": true,
  "uebungen": [
    {
      "name": "Name der Übung oder des Workouts",
      "details": "Sätze, Wiederholungen, Gewichte, Distanzen oder Workout-Inhalt"
    }
  ]
}

Antworte ohne Markdown-Codeblock und ohne zusätzlichen Text.
""".strip()



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


# ============================================================
# TABS
# ============================================================

# Die Variablen werden bewusst in dieser Reihenfolge zugeordnet:
# Trainingsdetails erscheinen als dritter Tab, Historie ganz rechts.
tab1, tab2, tab4, tab3 = st.tabs(
    [
        "🏋️ Training eintragen",
        "🧠 Mein Coach",
        "🔎 Trainingsdetails",
        "📅 Historie",
    ]
)


# ============================================================
# TAB 1: WORKOUT EINTRAGEN
# ============================================================

with tab1:
    st.subheader(
        "Neues Workout erfassen"
    )

    user_name = st.text_input(
        "Benutzername",
        value=st.session_state[
            "athleten_name"
        ],
        placeholder="Dein Benutzername",
        help=(
            "Ziel und Level werden automatisch "
            "aus dem Tabellenblatt „users“ geladen."
        ),
    ).strip()

    st.session_state[
        "athleten_name"
    ] = user_name

    user_profile = None
    profile_error = None

    if user_name:
        if conn is None:
            profile_error = (
                "Das Athletenprofil kann nicht geladen "
                "werden, weil Google Sheets nicht "
                "verbunden ist."
            )
        else:
            try:
                user_profiles = read_user_profiles(
                    conn=conn,
                    spreadsheet_url=SHEET_URL,
                    worksheet_name=(
                        USERS_WORKSHEET_NAME
                    ),
                )

                user_profile = get_user_profile(
                    user_profiles,
                    user_name,
                )

            except Exception as exc:
                profile_error = str(exc)

    if user_profile is not None:
        user_name = user_profile[
            "username"
        ]
        sportart = user_profile[
            "goal"
        ]
        level = user_profile[
            "level"
        ]

        st.session_state[
            "athleten_name"
        ] = user_name
        st.session_state[
            "sportart"
        ] = sportart
        st.session_state[
            "athleten_level"
        ] = level
        st.session_state[
            "user_profile_loaded"
        ] = True

        profile_col1, profile_col2 = (
            st.columns(2)
        )

        profile_col1.metric(
            "Primäres Ziel",
            sportart,
        )
        profile_col2.metric(
            "Trainingslevel",
            level,
        )

    else:
        sportart = ""
        level = ""

        st.session_state[
            "sportart"
        ] = ""
        st.session_state[
            "athleten_level"
        ] = ""
        st.session_state[
            "user_profile_loaded"
        ] = False

        if profile_error:
            st.error(profile_error)
        elif user_name:
            st.warning(
                "Dieser Benutzername wurde im "
                "Tabellenblatt „users“ nicht gefunden."
            )

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
        input_type = st.radio(
            "Wie möchtest du das Workout eintragen?",
            [
                "Foto hochladen / machen",
                "Als Text eintippen",
            ],
            horizontal=True,
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
            == "Foto hochladen / machen"
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

                encoded_image = (
                    base64.b64encode(
                        photo.getvalue()
                    ).decode("utf-8")
                )

                content_payload = [
                    {
                        "type": "text",
                        "text": (
                            WORKOUT_EXTRACTION_PROMPT
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": (
                            f"data:{mime_type};base64,"
                            f"{encoded_image}"
                        ),
                    },
                ]

                model_to_use = (
                    MISTRAL_VISION_MODEL
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
                content_payload = (
                    f"{WORKOUT_EXTRACTION_PROMPT}\n\n"
                    "Hier sind die zu analysierenden "
                    "Workout-Daten:\n\n"
                    f"{workout_text_input.strip()}"
                )

                model_to_use = (
                    MISTRAL_TEXT_MODEL
                )

        if should_analyze:
            with st.spinner(
                "Workout wird strukturiert "
                "und geprüft ..."
            ):
                try:
                    raw_result = call_mistral(
                        api_key=(
                            MISTRAL_API_KEY
                        ),
                        model=model_to_use,
                        content=(
                            content_payload
                        ),
                    )

                    workout_data = (
                        parse_workout_response(
                            raw_result
                        )
                    )

                except (
                    RuntimeError,
                    ValueError,
                ) as exc:
                    st.error(
                        "Analyse fehlgeschlagen: "
                        f"{exc}"
                    )

                else:
                    st.session_state[
                        "letzter_workout_input"
                    ] = workout_data

                
                    try:
                        classified_workout = (
                            classify_workout(
                                api_key=MISTRAL_API_KEY,
                                model=MISTRAL_TEXT_MODEL,
                                exercises=workout_data.get(
                                    "uebungen",
                                    [],
                                ),
                                user_rpe=None,
                                sport_goal=sportart,
                            )
                        )

                    except (
                        RuntimeError,
                        ValueError,
                    ) as exc:
                        st.session_state[
                            "letzte_workout_klassifikation"
                        ] = None

                        st.warning(
                            "Das Workout wurde erkannt, "
                            "aber die Trainingsklassifikation "
                            "ist fehlgeschlagen: "
                            f"{exc}"
                        )

                    else:
                        st.session_state[
                            "letzte_workout_klassifikation"
                        ] = classified_workout

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

                        st.success(
                            "Workout erfolgreich "
                            "strukturiert."
                        )

        current_workout = (
            st.session_state.get(
                "letzter_workout_input"
            )
        )

        if current_workout:
            st.markdown("---")
            st.write(
                "### Aktuell erfasstes Training"
            )

            for exercise in (
                current_workout.get(
                    "uebungen",
                    [],
                )
            ):
                exercise_name = (
                    exercise.get(
                        "name",
                        "Unbekannte Übung",
                    )
                )

                exercise_details = (
                    exercise.get(
                        "details",
                        "",
                    )
                )

                st.markdown(
                    f"**🏋️ {exercise_name}**"
                )

                if exercise_details:
                    st.write(
                        exercise_details
                    )

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
# TAB 2: STATUS UND COACH-FEEDBACK
# ============================================================

with tab2:
    st.subheader(
        "📊 Trainingsanalyse und Belastung"
    )

    training_data = (
        st.session_state.get(
            "letzter_workout_input"
        )
    )

    if not training_data:
        st.info(
            "Trage zuerst im ersten Tab "
            "ein Training ein."
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

        exercises = training_data.get(
            "uebungen",
            [],
        )

        classified_workout = (
            st.session_state.get(
                "letzte_workout_klassifikation"
            )
        )

        training_dimensions = None

        if classified_workout:
            training_dimensions = (
                calculate_classification_dimensions(
                    classified_workout,
                    user_rpe=user_rpe,
                )
            )

        st.write(training_dimensions["movement_pattern_load"])

        if training_dimensions is None:
            training_dimensions = {
                "movement_pattern_load": {},
                "muscle_group_load": {},
                "training_goal_counts": {},
                "load_type_load": {},
                "volume_totals": {},
                "review_required": [],
            }

        st.session_state[
            "letzte_trainingsdimensionen"
        ] = training_dimensions

        structural_score = (
            calculate_structural_score(
                exercises
            )
        )

        total_score = (
            calculate_load_score(
                structural_score=(
                    structural_score
                ),
                rpe=user_rpe,
                duration_minutes=(
                    duration_minutes
                ),
                level=user_level,
            )
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

        current_workout_text = (
            format_workout_as_text(
                exercises
            )
        )

        # ----------------------------------------------------
        # HISTORIE LADEN
        # ----------------------------------------------------

        try:
            training_history = get_user_training_history(
                conn=conn,
                spreadsheet_url=SHEET_URL,
                worksheet_name=WORKSHEET_NAME,
                columns=SHEET_COLUMNS,
                athlete_name=user_name,
                days=90,
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

        # with st.expander(
        #     "🔧 Technische Analyse-Eingabedaten",
        #     expanded=False,
        # ):
        #     st.write(
        #         "Historieneinträge:",
        #         len(training_history),
        #     )

        #     st.write(
        #         "Anzahl Einheiten:",
        #         history_summary.get(
        #             "anzahl_einheiten"
        #         ),
        #     )

        #     st.write(
        #         "Windows:",
        #     )
        #     st.json(
        #         history_summary.get(
        #             "windows",
        #             {},
        #         )
        #     )

        #     st.write(
        #         "Days since last load:",
        #     )
        #     st.json(
        #         history_summary.get(
        #             "days_since_last_load",
        #             {},
        #         )
        #     )

        #     st.write(
        #         "Overload signals:",
        #     )
        #     st.json(
        #         history_summary.get(
        #             "overload_signals",
        #             [],
        #         )
        #     )

        #     st.write(
        #         "Undertraining signals:",
        #     )
        #     st.json(
        #         history_summary.get(
        #             "undertraining_signals",
        #             [],
        #         )
        #     )

        #     st.write(
        #         "Trend Analysis:",
        #     )
        #     st.json(
        #         trend_analysis
        #     )

        #     st.write(
        #         "Training Balance:",
        #     )
        #     st.json(
        #         training_balance
        #     )

        training_analysis = build_findings(
            history_summary,
            primary_goal=user_sport,
        )

        st.session_state[
            "letzte_trainingsanalyse"
        ] = training_analysis

        # ----------------------------------------------------
        # REGELBASIERTE COACH-GRUNDLAGE
        # ----------------------------------------------------

        readiness = build_readiness_summary(
            history_summary=history_summary,
            training_analysis=training_analysis,
        )

        weekly_focus = build_weekly_focus(
            training_analysis=training_analysis,
            primary_goal=user_sport,
            training_balance=training_balance,
        )

        positive_observations = build_positive_observations(
            history_summary=history_summary,
            training_analysis=training_analysis,
        )

        # ----------------------------------------------------
        # KI-COACH EINMALIG ERZEUGEN
        # ----------------------------------------------------

        coach_state_key = create_coach_state_key(
            name=user_name,
            sportart=user_sport,
            level=user_level,
            duration_minutes=duration_minutes,
            rpe=user_rpe,
            score=total_score,
            injuries=user_injuries,
            comment=user_comment,
            exercises=exercises,
            history_summary=history_summary,
            training_analysis=training_analysis,
        )

        if st.session_state.get("letzter_state_key") != coach_state_key:
            with st.spinner(
                "Coach analysiert aktuelles Training und Trainingshistorie ..."
            ):
                try:
                    coach_text = get_coach_feedback(
                        api_key=MISTRAL_API_KEY,
                        model=MISTRAL_TEXT_MODEL,
                        user_name=user_name,
                        user_sport=user_sport,
                        user_level=user_level,
                        duration_minutes=duration_minutes,
                        user_rpe=user_rpe,
                        total_score=total_score,
                        status_text=status_text,
                        user_injuries=user_injuries,
                        user_comment=user_comment,
                        exercises=exercises,
                        history_summary=history_summary,
                        training_analysis=training_analysis,
                        readiness=readiness,
                        weekly_focus=weekly_focus,
                        positive_observations=positive_observations,
                    )
                except RuntimeError as exc:
                    print(f"Coach-Feedback fehlgeschlagen: {exc}")
                    coach_text = (
                        "Coach-Zusammenfassung\n\n"
                        "Das Coach-Feedback konnte momentan nicht erstellt werden. "
                        "Bitte versuche es erneut.\n\n"
                        "Nächste Einheit\n\n"
                        f"- **Fokus:** {weekly_focus.get('title', 'kontrollierter Trainingsreiz')}\n"
                        f"- **Vorschlag:** {weekly_focus.get('session', '20–30 Minuten lockere Bewegung')}"
                    )

                st.session_state["letzter_coach_text"] = coach_text
                st.session_state["letzter_state_key"] = coach_state_key

        coach_display_text = (
            st.session_state.get("letzter_coach_text")
            or "Noch kein Coach-Feedback verfügbar."
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
                "exercises": exercises,
                "injuries": user_injuries,
                "comment": user_comment,
                "classification": classified_workout,
                "training_dimensions": training_dimensions,
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
                                training_dimensions.get(
                                    "movement_pattern_load", {}
                                )
                            ),
                            "muskelgruppen_json": json_dumps_for_sheet(
                                training_dimensions.get(
                                    "muscle_group_load", {}
                                )
                            ),
                            "trainingsziele_json": json_dumps_for_sheet(
                                training_dimensions.get(
                                    "training_goal_counts", {}
                                )
                            ),
                            "belastungsarten_json": json_dumps_for_sheet(
                                training_dimensions.get(
                                    "load_type_load", {}
                                )
                            ),
                            "trainingsvolumen_json": json_dumps_for_sheet(
                                training_dimensions.get(
                                    "volume_totals", {}
                                )
                            ),
                            "klassifikation_json": json_dumps_for_sheet(
                                classified_workout or {}
                            ),
                        }
                    ],
                    columns=SHEET_COLUMNS,
                )

                try:
                    existing_data = read_workout_history(
                        conn=conn,
                        spreadsheet_url=SHEET_URL,
                        worksheet_name=WORKSHEET_NAME,
                        columns=SHEET_COLUMNS,
                    )

                    updated_data = pd.concat(
                        [existing_data, new_entry],
                        ignore_index=True,
                    )

                    write_workout_history(
                        conn=conn,
                        spreadsheet_url=SHEET_URL,
                        worksheet_name=WORKSHEET_NAME,
                        dataframe=updated_data,
                        columns=SHEET_COLUMNS,
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
            training_analysis.get(
                "overview",
                {},
            )
        )

        finding_count = int(
            analysis_overview.get(
                "finding_count",
                len(
                    training_analysis.get(
                        "findings",
                        [],
                    )
                ),
            )
            or 0
        )

        render_coach_dashboard(
            user_name=user_name,
            user_sport=user_sport,
            user_level=user_level,
            sessions_28=sessions_28,
            readiness=readiness,
            positive_observations=positive_observations,
            weekly_focus=weekly_focus,
            coach_text=coach_display_text,
            load_trend=load_trend,
            consistency=consistency,
            diversity=diversity,
        )

        # ----------------------------------------------------
        # CROSSFIT DASHBOARD
        # ----------------------------------------------------

        if str(user_sport).casefold() == "crossfit":

            st.divider()

            render_crossfit_dashboard(
                history_summary=history_summary,
            )


# ============================================================
# TAB 3: HISTORIE
# ============================================================

with tab3:
    st.subheader(
        "📅 Persönliche Trainingshistorie"
    )

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
            history_df = (
                read_workout_history(
                    conn=conn,
                    spreadsheet_url=(
                        SHEET_URL
                    ),
                    worksheet_name=(
                        WORKSHEET_NAME
                    ),
                    columns=(
                        SHEET_COLUMNS
                    ),
                )
            )

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
 
                for i, value in enumerate(history_display["zeitstempel"]):
                    if isinstance(value, type):
                        print("TYPE-OBJEKT:", i, value, repr(value))

                for i, value in enumerate(history_display["zeitstempel"]):
                    if isinstance(value, type):
                        print("FEHLER:", i, value)

                    if type(value).__name__ == "StringDtype":
                        print("STRINGDTYPE:", i, value)


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
# TAB 3: TRAININGSDETAILS
# ============================================================

with tab4:
    st.subheader(
        "🔎 Trainingsdetails"
    )

    if not training_data:
        st.info(
            "Trage zuerst im ersten Tab ein Training ein, "
            "um die detaillierte Trainingsanalyse zu laden."
        )

    else:
        safe_user_name = html.escape(
            str(user_name or "Unbekannt")
        )
        safe_user_sport = html.escape(
            str(user_sport or "Nicht angegeben")
        )
        safe_user_level = html.escape(
            str(user_level or "Nicht angegeben")
        )

        st.markdown(
            f"""
            <div class="welcome-card">
                <div class="welcome-title">
                    Willkommen zurück, {safe_user_name}
                </div>
                <div>
                    {safe_user_sport} &nbsp;·&nbsp; {safe_user_level}
                    &nbsp;·&nbsp; {sessions_28} Workouts in 28 Tagen
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        smart_left, smart_right = st.columns(
            [1, 1.35],
            gap="large",
        )

        with smart_left:
            st.markdown(
                f"""
                <div class="readiness-card {readiness['css_class']}">
                    <div class="muted-label">Trainings-Check-in</div>
                    <div class="readiness-title">
                        {readiness['icon']} {html.escape(readiness['label'])}
                    </div>
                    <div>{html.escape(readiness['detail'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with smart_right:
            st.markdown(
                f"""
                <div class="focus-card">
                    <div class="muted-label">Fokus der nächsten Tage</div>
                    <div class="readiness-title">
                        {html.escape(weekly_focus['title'])}
                    </div>
                    <div>{html.escape(weekly_focus['text'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("#### Was gut läuft")
        positive_columns = st.columns(
            len(positive_observations)
        )
        for column, observation in zip(
            positive_columns,
            positive_observations,
        ):
            with column:
                st.markdown(
                    f"""
                    <div class="positive-card">
                        <strong>✓</strong>&nbsp;
                        {html.escape(observation)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        dashboard_col1, dashboard_col2, dashboard_col3, dashboard_col4 = (
            st.columns(4)
        )

        dashboard_col1.metric(
            "Aktuell · 7 Tage",
            f"{sessions_7} Einheiten",
            (
                f"Ø RPE {average_rpe_7:.1f}"
                if average_rpe_7 > 0
                else None
            ),
        )
        dashboard_col2.metric(
            "Unterrepräsentiert · 28 Tage",
            int(balance_overview.get("underrepresented", 0) or 0),
            "über alle Trainingsbereiche",
        )
        dashboard_col3.metric(
            "Überrepräsentiert · 28 Tage",
            int(balance_overview.get("overrepresented", 0) or 0),
            "über alle Trainingsbereiche",
        )
        dashboard_col4.metric(
            "Trainingsroutine · 28 Tage",
            consistency.get(
                "text",
                "Noch nicht bewertbar",
            ),
            (
                f"{consistency.get('active_weeks', 0)} von 4 Wochen aktiv"
            ),
        )

        st.markdown("### Detaillierte Trainingsanalyse")

        st.markdown("#### Trainingsbalance · 28 Tage")
        st.caption(
            "Zielabhängige Einordnung der Trainingsbestandteile. "
            "Der Trend zeigt die letzten 14 Tage im Vergleich zu den "
            "vorherigen 14 Tagen. Unterrepräsentiert bedeutet nicht "
            "automatisch Untertraining, sondern eine relevante Lücke "
            "im aktuellen Trainingsmix."
        )

        balance_tab1, balance_tab2, balance_tab3, balance_tab4 = st.tabs(
            [
                "Bewegungsmuster",
                "Trainingsarten",
                "Muskelgruppen",
                "Belastungsarten",
            ]
        )

        with balance_tab1:
            render_balance_dimension(
                "Bewegungsmuster",
                training_balance.get("movement_patterns", []),
                max_rows=11,
            )

        with balance_tab2:
            render_balance_dimension(
                "Trainingsarten / Trainingsziele",
                training_balance.get("training_goals", []),
                max_rows=12,
            )

        with balance_tab3:
            render_balance_dimension(
                "Muskelgruppen",
                training_balance.get("muscle_groups", []),
                max_rows=12,
            )

        with balance_tab4:
            render_balance_dimension(
                "Belastungsarten",
                training_balance.get("load_types", []),
                max_rows=10,
            )

        st.markdown("#### Priorisierte Balance-Hinweise")

        if balance_findings:
            finding_columns = st.columns(2, gap="large")
            for index, finding in enumerate(balance_findings[:6]):
                with finding_columns[index % 2]:
                    st.markdown(
                        f"""
                        <div class="finding-card">
                            <div class="muted-label">TRAININGSBALANCE</div>
                            <strong>{html.escape(str(finding.get('title', 'Hinweis')))}</strong>
                            <div>{html.escape(str(finding.get('text', '')))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.success(
                "Die erfassten Trainingsbestandteile liegen aktuell "
                "innerhalb der hinterlegten Zielkorridore."
            )

        st.markdown("#### Entwicklung · 14 Tage")
        st.caption(
            "Vergleich der letzten 14 Tage mit den "
            "vorherigen 14 Tagen."
        )

        trend_col1, trend_col2, trend_col3 = st.columns(
            3
        )

        trend_col1.metric(
            "Belastung",
            load_trend.get(
                "text",
                "Noch nicht bewertbar",
            ),
            (
                f"{load_trend.get('change_percent'):+.1f} %"
                if load_trend.get(
                    "change_percent"
                ) is not None
                else None
            ),
        )

        trend_col2.metric(
            "Trainingshäufigkeit",
            frequency_trend.get(
                "text",
                "Noch nicht bewertbar",
            ),
            (
                f"{frequency_trend.get('current_sessions', 0)} "
                "Einheiten"
            ),
        )

        trend_col3.metric(
            "Intensität",
            rpe_trend.get(
                "text",
                "Noch nicht bewertbar",
            ),
            (
                f"Ø RPE {rpe_trend.get('current_value', 0):.1f}"
                if float(
                    rpe_trend.get(
                        "current_value",
                        0,
                    )
                    or 0
                ) > 0
                else None
            ),
        )

        trend_detail_left, trend_detail_right = st.columns(
            2,
            gap="large",
        )

        with trend_detail_left:
            st.markdown("##### Trainingsziele")

            if goal_trends:
                for item in goal_trends[:4]:
                    st.write(
                        f"{item.get('symbol', '•')} "
                        f"{item.get('text', '')}"
                    )
            else:
                st.caption(
                    "Noch keine klaren Veränderungen "
                    "bei den Trainingszielen."
                )

        with trend_detail_right:
            st.markdown("##### Bewegungsmuster")

            if movement_trends:
                for item in movement_trends[:4]:
                    st.write(
                        f"{item.get('symbol', '•')} "
                        f"{item.get('text', '')}"
                    )
            else:
                st.caption(
                    "Noch keine klaren Veränderungen "
                    "bei den Bewegungsmustern."
                )

        overview_left, overview_right = st.columns(
            [1.65, 1],
            gap="large",
        )

        with overview_left:
            st.markdown("#### Ergänzend: Belastungsverlauf · 28 Tage")

            chart_history = training_history.copy()

            if not chart_history.empty:
                timestamp_column = (
                    "zeitstempel_parsed"
                    if "zeitstempel_parsed"
                    in chart_history.columns
                    else "zeitstempel"
                )

                chart_history[
                    "dashboard_date"
                ] = pd.to_datetime(
                    chart_history[
                        timestamp_column
                    ],
                    errors="coerce",
                    utc=True,
                )

                chart_history[
                    "dashboard_score"
                ] = pd.to_numeric(
                    chart_history.get(
                        "score",
                        0,
                    ),
                    errors="coerce",
                ).fillna(0)

                daily_load = (
                    chart_history
                    .dropna(
                        subset=[
                            "dashboard_date"
                        ]
                    )
                    .assign(
                        dashboard_date=lambda frame: (
                            frame[
                                "dashboard_date"
                            ].dt.date
                        )
                    )
                    .groupby(
                        "dashboard_date",
                        as_index=False,
                    )[
                        "dashboard_score"
                    ]
                    .sum()
                    .rename(
                        columns={
                            "dashboard_date": "zeitstempel",
                            "dashboard_score": "Belastung",
                        }
                    )
                    .set_index("zeitstempel")
                )

                if not daily_load.empty:
                    st.line_chart(
                        daily_load,
                        width="stretch",
                    )
                else:
                    st.info(
                        "Für den Belastungstrend fehlen "
                        "gültige Datumswerte."
                    )
            else:
                st.info(
                    "Der Belastungstrend erscheint nach "
                    "dem ersten gespeicherten Workout."
                )

        with overview_right:
            st.markdown("#### Aktuelles Workout")

            current_col1, current_col2 = (
                st.columns(2)
            )

            current_col1.metric(
                "Aktuelle Belastung",
                total_score,
            )
            current_col2.metric(
                "Findings",
                finding_count,
            )

            st.caption(
                f"7-Tage-Load: {load_7:.0f} · "
                f"Workoutdauer: {duration_minutes} Min. · "
                f"RPE: {user_rpe}/10"
            )

        quality_col1, quality_col2 = st.columns(
            2
        )

        quality_col1.metric(
            "Trainingsvielfalt · 28 Tage",
            diversity.get(
                "text",
                "Noch nicht bewertbar",
            ),
            f"{diversity.get('score', 0)} %",
        )
        quality_col2.metric(
            "Trainingsroutine · 28 Tage",
            consistency.get(
                "text",
                "Noch nicht bewertbar",
            ),
            (
                f"{consistency.get('active_weeks', 0)} "
                "von 4 Wochen aktiv"
            ),
        )

        mix_col, findings_col = st.columns(
            [1, 1],
            gap="large",
        )

        with mix_col:
            st.markdown("#### Trainingsmix · 28 Tage")

            goal_counts = (
                window_28.get(
                    "training_goals",
                    {},
                )
                or {}
            )

            if isinstance(
                goal_counts,
                dict,
            ) and goal_counts:
                goal_labels = {
                    "max_strength": "Maximalkraft",
                    "hypertrophy": "Muskelaufbau",
                    "strength_endurance": "Kraftausdauer",
                    "speed_strength": "Schnellkraft",
                    "explosive_strength": "Explosivkraft",
                    "aerobic_base": "Aerobe Basis",
                    "threshold": "Schwelle",
                    "vo2max": "VO₂max",
                    "anaerobic_capacity": "Anaerob",
                    "technique": "Technik",
                    "mobility": "Mobilität",
                    "recovery": "Regeneration",
                }

                mix_data = pd.DataFrame(
                    [
                        {
                            "Trainingsziel": (
                                goal_labels.get(
                                    str(key),
                                    str(key).replace(
                                        "_",
                                        " ",
                                    ).title(),
                                )
                            ),
                            "Einheiten": float(
                                value
                            ),
                        }
                        for key, value
                        in goal_counts.items()
                        if float(
                            value or 0
                        ) > 0
                    ]
                )

                if not mix_data.empty:
                    mix_data = (
                        mix_data.sort_values(
                            "Einheiten",
                            ascending=False,
                        )
                        .set_index(
                            "Trainingsziel"
                        )
                    )

                    st.bar_chart(
                        mix_data,
                        horizontal=True,
                        width="stretch",
                    )
                else:
                    st.info(
                        "Noch kein Trainingsmix verfügbar."
                    )
            else:
                st.info(
                    "Der Trainingsmix wird nach mehreren "
                    "klassifizierten Workouts sichtbar."
                )

        with findings_col:
            st.markdown("#### Gesamtbelastung & Regeneration")

            top_findings = (
                training_analysis.get(
                    "top_findings",
                    training_analysis.get(
                        "findings",
                        [],
                    ),
                )
                or []
            )[:3]

            if not top_findings:
                st.success(
                    "Aktuell wurden keine relevanten "
                    "Auffälligkeiten erkannt."
                )
            else:
                for finding in top_findings:
                    finding_title = str(
                        finding.get(
                            "title",
                            "Trainingshinweis",
                        )
                    )
                    recommendation = str(
                        finding.get(
                            "recommendation",
                            "",
                        )
                    )
                    severity = str(
                        finding.get(
                            "severity",
                            "notice",
                        )
                    ).title()

                    st.markdown(
                        f"""
                        <div class="finding-card">
                            <div class="muted-label">{severity}</div>
                            <strong>{finding_title}</strong>
                            <div>{recommendation}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # with st.expander(
        #     "🔧 Regelbasierte Trainingsanalyse",
        #     expanded=False,
        # ):
        #     st.json(training_analysis)

        # ----------------------------------------------------
        # AKTUELLE BELASTUNG
        # ----------------------------------------------------

        st.write(
            f"### Analyse für {user_name}"
        )

        metric_col1, metric_col2, metric_col3 = (
            st.columns(3)
        )

        metric_col1.metric(
            "Dauer",
            f"{duration_minutes} Min.",
        )

        metric_col2.metric(
            "RPE",
            f"{user_rpe} / 10",
        )

        metric_col3.metric(
            "Belastung",
            f"{total_score} Punkte",
        )

        st.write(
            f"**Trainingslevel:** "
            f"`{user_level}`"
        )

        st.write(
            f"**Level-Faktor:** "
            f"`× {level_factor:.2f}`"
        )

        st.write(
            "**Struktureller Workout-Wert:** "
            f"`{structural_score}`"
        )

       # if classified_workout:
            # with st.expander(
            #     "🔍 Erkannte Trainingsklassifikation",
            #     expanded=False,
            # ):
            #     classified_exercises = (
            #         classified_workout.get(
            #             "uebungen",
            #             [],
            #         )
            #     )

            #     if not classified_exercises:
            #         st.caption(
            #             "Keine klassifizierten Übungen verfügbar."
            #         )

            #     for exercise in classified_exercises:
            #         exercise_name = (
            #             exercise.get("canonical_name")
            #             or exercise.get("name")
            #             or "Unbekannte Übung"
            #         )

            #         st.markdown(
            #             f"### {exercise_name}"
            #         )

            #         patterns = [
            #             item.get("type")
            #             for item in exercise.get(
            #                 "movement_patterns",
            #                 [],
            #             )
            #             if item.get("type")
            #         ]

            #         muscles = [
            #             item.get("type")
            #             for item in exercise.get(
            #                 "muscle_groups",
            #                 [],
            #             )
            #             if item.get("type")
            #         ]

            #         load_types = [
            #             item.get("type")
            #             for item in exercise.get(
            #                 "load_types",
            #                 [],
            #             )
            #             if item.get("type")
            #         ]

            #         training_goal = (
            #             exercise.get(
            #                 "training_goal",
            #                 {},
            #             ).get("type")
            #         )

            #         st.write(
            #             "**Bewegungsmuster:**",
            #             ", ".join(patterns)
            #             or "Nicht erkannt",
            #         )

            #         st.write(
            #             "**Muskelgruppen:**",
            #             ", ".join(muscles)
            #             or "Nicht erkannt",
            #         )

            #         st.write(
            #             "**Trainingsziel:**",
            #             training_goal
            #             or "Nicht sicher bestimmbar",
            #         )

            #         st.write(
            #             "**Belastungsarten:**",
            #             ", ".join(load_types)
            #             or "Nicht erkannt",
            #         )

            #         st.write(
            #             "**Konfidenz:**",
            #             exercise.get(
            #                 "overall_confidence",
            #                 0,
            #             ),
            #         )

            #         if exercise.get(
            #             "review_status"
            #         ) != "approved":
            #             st.warning(
            #                 "Diese Zuordnung sollte "
            #                 "manuell geprüft werden."
            #             )

        #if training_dimensions:
            # with st.expander(
            #     "📊 Aggregierte Trainingsdaten",
            #     expanded=False,
            # ):
            #     st.write(
            #         "**Bewegungsmuster-Belastung**"
            #     )

            #     st.json(
            #         training_dimensions[
            #             "movement_pattern_load"
            #         ]
            #     )

            #     st.write(
            #         "**Muskelgruppen-Belastung**"
            #     )

            #     st.json(
            #         training_dimensions[
            #             "muscle_group_load"
            #         ]
            #     )

            #     st.write(
            #         "**Trainingsziele**"
            #     )

            #     st.json(
            #         training_dimensions[
            #             "training_goal_counts"
            #         ]
            #     )

            #     st.write(
            #         "**Belastungsarten**"
            #     )

            #     st.json(
            #         training_dimensions[
            #             "load_type_load"
            #         ]
            #     )

            #     st.write(
            #         "**Trainingsvolumen**"
            #     )

            #     st.json(
            #         training_dimensions[
            #             "volume_totals"
            #         ]
            #     )

            #     st.caption(
            #         "Der Belastungswert ist eine grobe "
            #         "MVP-Schätzung aus Dauer, RPE und "
            #         "erkannten Workout-Inhalten. "
            #         "Er ersetzt keine medizinische oder "
            #         "sportwissenschaftliche Diagnostik."
            #     )

        # ----------------------------------------------------
        # HISTORIENZUSAMMENFASSUNG ANZEIGEN
        # ----------------------------------------------------

        # with st.expander(
        #     "📚 Verwendete Trainingshistorie"
        # ):
        #     st.write(
        #         "**Analysierter Zeitraum:** "
        #         f"{history_summary.get('zeitraum_tage', 90)} Tage"
        #     )

        #     st.write(
        #         "**Analysierte frühere Einheiten:** "
        #         f"{history_summary.get('anzahl_einheiten', 0)}"
        #     )

        #     st.write(
        #         "**Einheiten der letzten 7 Tage:** "
        #         f"{history_summary.get('einheiten_letzte_7_tage', 0)}"
        #     )

        #     average_rpe = (
        #         history_summary.get(
        #             "durchschnittliche_rpe"
        #         )
        #     )

        #     if average_rpe is not None:
        #         st.write(
        #             "**Durchschnittliche RPE:** "
        #             f"{average_rpe}"
        #         )

        #     current_week_load = (
        #         history_summary.get(
        #             "belastung_letzte_7_tage"
        #         )
        #     )

        #     previous_week_load = (
        #         history_summary.get(
        #             "belastung_vorherige_7_tage"
        #         )
        #     )

        #     if (
        #         current_week_load
        #         is not None
        #     ):
        #         st.write(
        #             "**Belastung letzte 7 Tage:** "
        #             f"{current_week_load}"
        #         )

        #     if (
        #         previous_week_load
        #         is not None
        #     ):
        #         st.write(
        #             "**Belastung vorherige 7 Tage:** "
        #             f"{previous_week_load}"
        #         )

        #     load_change = (
        #         history_summary.get(
        #             "belastungsveraenderung_prozent"
        #         )
        #     )

        #     if load_change is not None:
        #         st.write(
        #             "**Belastungsveränderung "
        #             "gegenüber der vorherigen Woche:** "
        #             f"{load_change:+.1f} %"
        #         )

        #     high_rpe_count = (
        #         history_summary.get(
        #             "einheiten_mit_rpe_ab_8",
        #             0,
        #         )
        #     )

        #     st.write(
        #         "**Einheiten mit RPE ≥ 8:** "
        #         f"{high_rpe_count}"
        #     )

        #     st.write(
        #         "**Erkannte Trainingskategorien:**"
        #     )

        #     categories = (
        #         history_summary.get(
        #             "trainingskategorien",
        #             {},
        #         )
        #     )

        #     if categories:
        #         st.json(categories)
        #     else:
        #         st.caption(
        #             "Noch keine Trainingskategorien "
        #             "aus früheren Einheiten erkannt."
        #         )

        #     complaints = (
        #         history_summary.get(
        #             "gemeldete_beschwerden",
        #             [],
        #         )
        #     )

        #     if complaints:
        #         st.write(
        #             "**Gemeldete Beschwerden "
        #             "in der Historie:**"
        #         )

        #         for complaint in complaints:
        #             st.markdown(
        #                 f"- {complaint}"
        #             )