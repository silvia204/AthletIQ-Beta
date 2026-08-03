import json
from typing import Any

import requests


MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def call_mistral(
    *,
    api_key: str,
    model: str,
    content: str | list[dict[str, Any]],
    timeout: int = 90,
) -> str:
    """
    Sendet eine Anfrage an die Mistral Chat-Completions-API.
    """

    if not api_key.strip():
        raise RuntimeError(
            "Der Mistral-API-Key ist leer."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
        "temperature": 0,
    }

    try:
        response = requests.post(
            MISTRAL_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        response.raise_for_status()

    except requests.Timeout as exc:
        raise RuntimeError(
            "Die Anfrage an Mistral hat zu lange gedauert."
        ) from exc

    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Mistral konnte nicht erreicht werden."
        ) from exc

    except requests.HTTPError as exc:
        response_text = response.text[:1500]

        raise RuntimeError(
            f"Mistral meldet HTTP {response.status_code}: "
            f"{response_text}"
        ) from exc

    try:
        response_data = response.json()

        return str(
            response_data["choices"][0]["message"]["content"]
        ).strip()

    except (
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise RuntimeError(
            "Mistral hat ein unerwartetes Antwortformat geliefert."
        ) from exc


def remove_markdown_code_fence(text: str) -> str:
    """
    Entfernt optionale Markdown-Codeblöcke aus KI-Antworten.
    """

    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()

    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned


def parse_workout_response(
    raw_text: str,
) -> dict[str, Any]:
    """
    Prüft und bereinigt die strukturierte Workout-Antwort.
    """

    cleaned_text = remove_markdown_code_fence(
        raw_text
    )

    try:
        data = json.loads(cleaned_text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Die KI-Antwort war kein gültiges JSON."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "Die KI-Antwort muss ein JSON-Objekt sein."
        )

    exercises = data.get("uebungen")

    if not isinstance(exercises, list):
        raise ValueError(
            "In der KI-Antwort fehlt die Liste 'uebungen'."
        )

    cleaned_exercises: list[dict[str, str]] = []

    for exercise in exercises:
        if not isinstance(exercise, dict):
            continue

        name = str(
            exercise.get("name", "")
        ).strip()

        details = str(
            exercise.get("details", "")
        ).strip()

        if not name:
            continue

        cleaned_exercises.append(
            {
                "name": name,
                "details": details,
            }
        )

    if not cleaned_exercises:
        raise ValueError(
            "Es wurden keine verwertbaren Übungen erkannt."
        )

    return {
        "workout_erkannt": bool(
            data.get("workout_erkannt", True)
        ),
        "uebungen": cleaned_exercises,
    }