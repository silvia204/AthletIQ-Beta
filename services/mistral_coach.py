"""
mistral_coach.py

Erstellt das finale Coach-Feedback mit Mistral.

Diese Schicht enthält ausschließlich
Prompt Building und den LLM-Aufruf.
"""

from __future__ import annotations

import json

from models.training_analysis import (
    TrainingAnalysis,
)

from prompts.coach import (
    COACH_PROMPT,
    DAILY_COACH_TIPS_PROMPT,
)

from services.mistral_service import (
    call_mistral,
)


def build_coach_with_mistral(
    *,
    training_analysis: TrainingAnalysis,
    readiness: dict,
    weekly_focus: dict,
    positive_observations: list[str],
    history_summary: dict,
    sportart: str,
    level: str,
    injuries: str | None,
    api_key: str,
    model: str,
) -> str:
    """
    Erstellt den Prompt und ruft Mistral auf.
    """

    prompt = f"""
{COACH_PROMPT}

SPORTART
{sportart}

LEVEL
{level}

BESCHWERDEN
{injuries or "Keine"}


----------------------------------------

TRAINING ANALYSIS

{json.dumps(training_analysis.to_dict(), ensure_ascii=False, indent=2)}

----------------------------------------

READINESS

{json.dumps(readiness, ensure_ascii=False, indent=2)}

----------------------------------------

WEEKLY FOCUS

{json.dumps(weekly_focus, ensure_ascii=False, indent=2)}

----------------------------------------

POSITIVE OBSERVATIONS

{json.dumps(positive_observations, ensure_ascii=False, indent=2)}

----------------------------------------

HISTORY SUMMARY

{json.dumps(history_summary, ensure_ascii=False, indent=2)}
""".strip()

    return call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )


def build_daily_coach_tips(
    *,
    readiness: dict,
    weekly_focus: dict,
    training_analysis: TrainingAnalysis,
    history_summary: dict,
    sportart: str,
    level: str,
    workout_rpe: int | None,
    duration_minutes: int | None,
    injuries: str | None,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """
    Erstellt drei kompakte Daily-Coach-Tipps:
    Training, Ernährung und Recovery.
    """

    prompt = f"""
{DAILY_COACH_TIPS_PROMPT}

SPORTART
{sportart}

LEVEL
{level}

BESCHWERDEN
{injuries or "Keine"}

---

READINESS

{json.dumps(
    readiness,
    ensure_ascii=False,
    indent=2,
)}

---

WEEKLY FOCUS

{json.dumps(
    weekly_focus,
    ensure_ascii=False,
    indent=2,
)}

---

TRAINING ANALYSIS

{json.dumps(
    training_analysis.to_dict(),
    ensure_ascii=False,
    indent=2,
)}

---

HISTORY SUMMARY

{json.dumps(
    history_summary,
    ensure_ascii=False,
    indent=2,
)}
""".strip()

    response = call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )

    response = _remove_code_fence(
        response
    )

    try:
        data = json.loads(
            response
        )

    except json.JSONDecodeError:

        repair_prompt = f"""
Die folgende Antwort sollte ein gültiges JSON-Objekt sein,
enthält aber einen JSON-Syntaxfehler.

Korrigiere ausschließlich die JSON-Syntax.

Verändere keine Inhalte.
Ergänze keine Informationen.
Entferne keine Informationen.

Liefere ausschließlich gültiges JSON.
Kein Markdown.
Keine Code-Fences.
Keine Erklärung.

Fehlerhafte Antwort:

{response}
""".strip()

        repaired_response = call_mistral(
            api_key=api_key,
            model=model,
            content=repair_prompt,
        )

        repaired_response = _remove_code_fence(
            repaired_response
        )

        try:
            data = json.loads(
                repaired_response
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Daily Coach Tips konnten nicht als "
                "gültiges JSON verarbeitet werden."
            ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            "Daily Coach Tips haben ein "
            "unerwartetes Format."
        )

    return {
        "training": str(
            data.get(
                "training",
                "",
            )
        ).strip(),
        "nutrition": str(
            data.get(
                "nutrition",
                "",
            )
        ).strip(),
        "recovery": str(
            data.get(
                "recovery",
                "",
            )
        ).strip(),
    }


def _remove_code_fence(
    response: str,
) -> str:
    """
    Entfernt mögliche Markdown-Code-Fences
    aus einer Mistral-Antwort.
    """

    text = str(
        response or ""
    ).strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    return text