from typing import Any

import pandas as pd


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
        return pd.DataFrame(columns=columns)

    dataframe = pd.DataFrame(data)

    if dataframe.empty and len(dataframe.columns) == 0:
        return pd.DataFrame(columns=columns)

    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = ""

    dataframe = dataframe[columns].copy()
    dataframe = dataframe.fillna("")

    return dataframe


def prepare_dataframe_for_sheets(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """
    Entfernt Werte, die von der Google-Sheets-API
    nicht zuverlässig verarbeitet werden.
    """

    cleaned_data = dataframe.copy()

    for column in columns:
        if column not in cleaned_data.columns:
            cleaned_data[column] = ""

    cleaned_data = cleaned_data[columns]

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

    cleaned_data = cleaned_data.astype(object)

    for column in cleaned_data.columns:
        cleaned_data[column] = cleaned_data[column].map(
            lambda value: (
                value.item()
                if hasattr(value, "item")
                else value
            )
        )

    return cleaned_data


def write_workout_history(
    *,
    conn: Any,
    spreadsheet_url: str,
    worksheet_name: str,
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """
    Schreibt die komplette Workout-Historie zurück
    nach Google Sheets.
    """

    if conn is None:
        raise RuntimeError(
            "Google Sheets ist nicht verbunden."
        )

    cleaned_data = prepare_dataframe_for_sheets(
        dataframe,
        columns,
    )

    conn.update(
        spreadsheet=spreadsheet_url,
        worksheet=worksheet_name,
        data=cleaned_data,
    )