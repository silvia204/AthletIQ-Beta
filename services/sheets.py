"""
Google-Sheets-Zugriff für die Trainingshistorie.

Workouts werden beim normalen Speichern als neue Zeilen an das
bestehende Worksheet angehängt. Die vollständige Historie muss dadurch
nicht bei jedem neuen Workout erneut geschrieben werden.
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    Timeout as RequestsTimeout,
)


def read_workout_history(
    *,
    conn: Any,
    spreadsheet_url: str,
    worksheet_name: str,
    columns: list[str],
) -> pd.DataFrame:
    """
    Liest das Workout-Sheet und stellt alle erwarteten
    Spalten bereit.
    """

    if conn is None:
        raise RuntimeError(
            "Google Sheets ist nicht verbunden."
        )

    data = conn.read(
        spreadsheet=spreadsheet_url,
        worksheet=worksheet_name,
        ttl=0,
    )

    if data is None:
        return pd.DataFrame(
            columns=columns
        )

    dataframe = pd.DataFrame(data)

    if (
        dataframe.empty
        and len(dataframe.columns) == 0
    ):
        return pd.DataFrame(
            columns=columns
        )

    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = ""

    dataframe = dataframe[
        columns
    ].copy()

    dataframe = dataframe.fillna("")

    return dataframe


def prepare_dataframe_for_sheets(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """
    Bereitet einen DataFrame für Google Sheets vor.

    - stellt alle erwarteten Spalten bereit
    - erzwingt die korrekte Spaltenreihenfolge
    - entfernt NaN und unendliche Werte
    - wandelt NumPy-Skalare in normale Python-Werte um
    """

    cleaned_data = dataframe.copy()

    for column in columns:
        if column not in cleaned_data.columns:
            cleaned_data[column] = ""

    cleaned_data = cleaned_data[
        columns
    ].copy()

    cleaned_data = cleaned_data.replace(
        {
            float("inf"): "",
            float("-inf"): "",
        }
    )

    cleaned_data = cleaned_data.where(
        pd.notna(cleaned_data),
        "",
    )

    cleaned_data = cleaned_data.astype(
        object
    )

    for column in cleaned_data.columns:
        cleaned_data[column] = (
            cleaned_data[column].map(
                lambda value: (
                    value.item()
                    if hasattr(
                        value,
                        "item",
                    )
                    else value
                )
            )
        )

    return cleaned_data


def _get_worksheet(
    *,
    conn: Any,
    spreadsheet_url: str,
    worksheet_name: str,
) -> Any:
    """
    Holt das zugrunde liegende gspread-Worksheet.

    Dadurch kann append_rows() verwendet werden, ohne das komplette
    Worksheet über conn.update() neu zu schreiben.
    """

    if conn is None:
        raise RuntimeError(
            "Google Sheets ist nicht verbunden."
        )

    gsheets_client = getattr(
        conn,
        "client",
        None,
    )

    if gsheets_client is None:
        raise RuntimeError(
            "Der Google-Sheets-Client ist nicht verfügbar."
        )

    select_worksheet = getattr(
        gsheets_client,
        "_select_worksheet",
        None,
    )

    if select_worksheet is None:
        raise RuntimeError(
            "Das Google-Sheets-Worksheet kann mit der "
            "installierten streamlit-gsheets-Version "
            "nicht direkt ausgewählt werden."
        )

    return select_worksheet(
        spreadsheet=spreadsheet_url,
        worksheet=worksheet_name,
    )


def append_workout_history(
    *,
    conn: Any,
    spreadsheet_url: str,
    worksheet_name: str,
    dataframe: pd.DataFrame,
    columns: list[str],
    max_attempts: int = 3,
) -> None:
    """
    Hängt neue Workout-Zeilen an die bestehende Historie an.

    Im Gegensatz zu conn.update() wird das bestehende Worksheet
    nicht geleert und vollständig neu geschrieben.

    Temporäre Netzwerkfehler werden mit kurzem Backoff erneut
    versucht.

    Hinweis:
    Ein Retry nach einem Verbindungsabbruch kann theoretisch zu
    einem Duplikat führen, wenn Google die Zeile bereits gespeichert
    hat, die erfolgreiche Antwort aber nicht mehr beim Client ankam.
    Eine stabile workout_id kann dieses Risiko später vollständig
    absichern.
    """

    if conn is None:
        raise RuntimeError(
            "Google Sheets ist nicht verbunden."
        )

    if max_attempts < 1:
        raise ValueError(
            "max_attempts muss mindestens 1 sein."
        )

    cleaned_data = (
        prepare_dataframe_for_sheets(
            dataframe,
            columns,
        )
    )

    if cleaned_data.empty:
        return

    rows = cleaned_data.values.tolist()

    last_error: Exception | None = None

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            worksheet = _get_worksheet(
                conn=conn,
                spreadsheet_url=spreadsheet_url,
                worksheet_name=worksheet_name,
            )

            worksheet.append_rows(
                rows,
                value_input_option="RAW",
            )

            return

        except (
            RequestsConnectionError,
            RequestsTimeout,
            ConnectionResetError,
            ConnectionError,
            TimeoutError,
        ) as exc:
            last_error = exc

            if attempt >= max_attempts:
                break

            # 1 Sekunde nach Versuch 1,
            # 2 Sekunden nach Versuch 2.
            time.sleep(attempt)

    raise RuntimeError(
        "Google Sheets konnte nach "
        f"{max_attempts} Versuchen nicht aktualisiert werden."
    ) from last_error


def write_workout_history(
    *,
    conn: Any,
    spreadsheet_url: str,
    worksheet_name: str,
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """
    Schreibt die komplette Workout-Historie nach Google Sheets.

    Diese Funktion bleibt für bestehende Verwaltungs- oder
    Migrationsvorgänge erhalten.

    Für das normale Speichern eines neuen Workouts sollte
    append_workout_history() verwendet werden.
    """

    if conn is None:
        raise RuntimeError(
            "Google Sheets ist nicht verbunden."
        )

    cleaned_data = (
        prepare_dataframe_for_sheets(
            dataframe,
            columns,
        )
    )

    conn.update(
        spreadsheet=spreadsheet_url,
        worksheet=worksheet_name,
        data=cleaned_data,
    )