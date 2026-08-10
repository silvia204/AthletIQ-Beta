"""
mistral_interpreter.py

Kommuniziert mit Mistral, um ein Workout
sportwissenschaftlich zu interpretieren.
"""

from __future__ import annotations

from dataclasses import asdict
import json

from models.parsed_workout import ParsedWorkout
from models.deterministic_analysis import (
    DeterministicAnalysis,
)
from models.workout_interpretation import (
    WorkoutInterpretation,
)

from prompts.workout_interpretation import (
    WORKOUT_INTERPRETATION_PROMPT,
)

from services.mistral_service import (
    call_mistral,
    remove_markdown_code_fence,
)


def interpret_with_mistral(
    *,
    parsed_workout: ParsedWorkout,
    deterministic_analysis: DeterministicAnalysis,
    sportart: str,
    api_key: str,
    model: str,
) -> WorkoutInterpretation:
    """
    Führt die sportwissenschaftliche
    Interpretation eines Workouts durch.

    Falls Mistral syntaktisch ungültiges JSON liefert,
    wird genau ein Reparaturversuch durchgeführt.
    """

    prompt = (
        f"{WORKOUT_INTERPRETATION_PROMPT}\n\n"
        f"Sportart:\n{sportart}\n\n"
        f"ParsedWorkout:\n"
        f"{json.dumps(asdict(parsed_workout), indent=2)}\n\n"
        f"DeterministicAnalysis:\n"
        f"{json.dumps(deterministic_analysis.to_dict(), indent=2)}"
    )

    print("===== INTERPRETER PROMPT =====")
    print(prompt)
    print("==============================")

    response = call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )

    print("===== INTERPRETER RESPONSE =====")
    print(repr(response))
    print("================================")

    response = remove_markdown_code_fence(
        response
    )

    try:
        response_json = json.loads(
            response
        )

    except json.JSONDecodeError as exc:

        print(
            "===== INTERPRETER JSON FEHLER ====="
        )
        print(
            f"{exc.msg} | "
            f"Zeile {exc.lineno}, "
            f"Spalte {exc.colno}, "
            f"Position {exc.pos}"
        )
        print(
            "Starte einen JSON-Reparaturversuch."
        )
        print(
            "==================================="
        )

        response_json = _repair_json_response(
            broken_response=response,
            api_key=api_key,
            model=model,
        )

    if not isinstance(
        response_json,
        dict,
    ):
        raise ValueError(
            "Die Workout-Interpretation muss "
            "ein JSON-Objekt sein."
        )

    print("===== INTERPRETER JSON =====")
    print(response_json)
    print("============================")

    return _build_workout_interpretation(
        response_json
    )


def _repair_json_response(
    *,
    broken_response: str,
    api_key: str,
    model: str,
) -> dict:
    """
    Führt genau einen Reparaturversuch durch,
    wenn Mistral syntaktisch ungültiges JSON
    geliefert hat.

    Die Inhalte dürfen dabei nicht neu interpretiert
    oder fachlich verändert werden.
    """

    repair_prompt = (
        "Die folgende Antwort sollte ein gültiges "
        "JSON-Objekt sein, enthält aber einen "
        "JSON-Syntaxfehler.\n\n"
        "Korrigiere ausschließlich die JSON-Syntax.\n"
        "Verändere keine Inhalte.\n"
        "Ergänze keine neuen Informationen.\n"
        "Entferne keine Informationen.\n"
        "Interpretiere das Workout nicht erneut.\n\n"
        "WICHTIG:\n"
        "- Liefere ausschließlich gültiges JSON.\n"
        "- Kein Markdown.\n"
        "- Keine Code-Fences.\n"
        "- Keine Erklärung.\n"
        "- Keine Kommentare.\n\n"
        "Fehlerhafte JSON-Antwort:\n\n"
        f"{broken_response}"
    )

    repaired_response = call_mistral(
        api_key=api_key,
        model=model,
        content=repair_prompt,
    )

    print(
        "===== INTERPRETER REPAIR RESPONSE ====="
    )
    print(
        repr(repaired_response)
    )
    print(
        "======================================="
    )

    repaired_response = (
        remove_markdown_code_fence(
            repaired_response
        )
    )

    try:
        repaired_json = json.loads(
            repaired_response
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Mistral hat auch beim "
            "JSON-Reparaturversuch kein gültiges "
            "JSON geliefert. "
            f"Fehler: {exc.msg}, "
            f"Zeile {exc.lineno}, "
            f"Spalte {exc.colno}."
        ) from exc

    if not isinstance(
        repaired_json,
        dict,
    ):
        raise ValueError(
            "Der JSON-Reparaturversuch hat kein "
            "JSON-Objekt geliefert."
        )

    return repaired_json


def _build_workout_interpretation(
    data: dict,
) -> WorkoutInterpretation:

    return WorkoutInterpretation(

        trainingsziele=data.get(
            "trainingsziele",
            {},
        ),

        belastungsarten=data.get(
            "belastungsarten",
            {},
        ),

        klassifikation=data.get(
            "klassifikation",
            {},
        ),

        trainingsintention=data.get(
            "trainingsintention",
            "",
        ),

        besonderheiten=data.get(
            "besonderheiten",
            [],
        ),

        confidence=data.get(
            "confidence",
        ),
    )