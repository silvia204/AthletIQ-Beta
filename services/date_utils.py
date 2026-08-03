"""
Utilities for handling training dates consistently.
"""

from __future__ import annotations

import pandas as pd


def normalize_training_dates(
    df: pd.DataFrame,
    column: str = "zeitstempel",
) -> pd.DataFrame:
    """
    Converts mixed date formats into timezone-aware datetimes.
    """

    if column not in df.columns:
        return df

    df = df.copy()

    df[column] = (
        pd.to_datetime(
            df[column],
            errors="coerce",
            utc=True,
        )
        .dt.tz_convert("Europe/Berlin")
    )

    return df


def format_training_dates(
    df: pd.DataFrame,
    column: str = "zeitstempel",
    include_time: bool = False,
) -> pd.DataFrame:
    """
    Formats datetime values for display.
    """

    if column not in df.columns:
        return df

    df = df.copy()

    # Sicherheit: Falls die Spalte noch Strings enthält,
    # zuerst normalisieren.
    if not pd.api.types.is_datetime64_any_dtype(df[column]):
        df = normalize_training_dates(
            df,
            column=column,
        )

    if include_time:

        df[column] = (
            df[column]
            .dt.strftime("%d.%m.%Y %H:%M")
        )

    else:

        df[column] = (
            df[column]
            .dt.strftime("%d.%m.%Y")
        )

    return df

def sort_training_history(
    df: pd.DataFrame,
    column: str = "zeitstempel",
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Normalize and sort training history by date.

    Parameters
    ----------
    df
        Training history DataFrame.
    column
        Name of the date column.
    ascending
        Sort order. Default = newest first.
    """

    if column not in df.columns:
        return df

    df = normalize_training_dates(
        df,
        column=column,
    )

    return (
        df.sort_values(
            by=column,
            ascending=ascending,
        )
        .reset_index(drop=True)
    )