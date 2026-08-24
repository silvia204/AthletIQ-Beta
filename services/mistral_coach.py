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
    coach_context: dict,
    sportart: str,
    level: str,
    injuries: str | None,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """
    Erstellt Readiness-Summary und History-Coachtext aus zwei
    strikt getrennten Faktenblöcken.
    """

    readiness_facts = coach_context.get(
        "readiness_summary_facts",
        {},
    )
    history_facts = coach_context.get(
        "history_coach_facts",
        {},
    )

    prompt = f"""
{COACH_PROMPT}

SPORTART
{sportart}

LEVEL
{level}

BESCHWERDEN
{injuries or "Keine"}

----------------------------------------

FAKTEN NUR FÜR READINESS_SUMMARY

{json.dumps(readiness_facts, ensure_ascii=False, indent=2)}

----------------------------------------

FAKTEN NUR FÜR COACH_FEEDBACK

{json.dumps(history_facts, ensure_ascii=False, indent=2)}

----------------------------------------

TRENNUNG DER AUFGABEN

Für READINESS_SUMMARY darfst du ausschließlich den ersten
Faktenblock verwenden.

Für COACH_FEEDBACK darfst du ausschließlich den zweiten
Faktenblock verwenden.

Der COACH_FEEDBACK-Text darf den Readiness-Status, die
Overload-Signale oder eine kurzfristige Belastungsentscheidung
nicht aus dem ersten Faktenblock übernehmen.

TRAINING_RECENCY hat hohe Priorität:
- Wenn in den letzten 7 Tagen keine Einheit dokumentiert wurde,
  muss dies in der Einordnung ausdrücklich erwähnt werden.
- Eine hohe Zahl von Einheiten über 28 Tage darf dann nicht als
  aktuell durchgehend konsequenter Trainingsrhythmus bezeichnet
  werden.
- Beschreibe den Wechsel zwischen den jüngsten 7 Tagen und den
  7 Tagen davor rein faktisch.
- Leite aus Trainingshäufigkeit keine Regenerationsfähigkeit,
  Ausdauer oder sonstige Fähigkeit ab.

UNDERREPRESENTED_AREAS:
- bedeuten ausschließlich, dass diese Bereiche im betrachteten
  Zeitraum wenig oder nicht dokumentiert wurden.
- Bezeichne sie nicht als Defizit, Dysbalance oder Schwäche.
- Leite daraus keine gesundheitliche oder leistungsbezogene
  Wirkung ab.

TRAINING_PROFILE:
- beschreibt ausschließlich die relative Verteilung der bereits
  klassifizierten Trainingsdimensionen.
- Erfinde keine eigenen Übungen oder Klassifikationen.
- Eine hohe relative Häufigkeit ist keine Überlastung und eine
  niedrige relative Häufigkeit ist kein Defizit.

----------------------------------------

AUSGABEFORMAT

<READINESS_SUMMARY>
Kurzer Absatz.
</READINESS_SUMMARY>

<COACH_FEEDBACK>
3 bis 4 kurze zusammenhängende Absätze.
</COACH_FEEDBACK>

Schreibe nichts vor oder nach diesen Bereichen.

READINESS_SUMMARY:
- Verdichte nur die vorhandenen overload_signals.
- Keine zusätzlichen Ursachen, Folgen oder Empfehlungen.
- Sind keine overload_signals vorhanden, sage kurz, dass aktuell
  keine relevanten Überlastungswarnungen erkannt wurden.

COACH_FEEDBACK:
- Rein beschreibende Einordnung der Historie und ihrer Entwicklung.
- Keine Bulletpoints.
- Keine konkreten Übungen.
- Keine medizinischen oder gesundheitlichen Aussagen.
- Keine kurzfristige Trainingssteuerung.
- Kein "du solltest", "du musst", "reduziere" oder "nächste Einheit".
- Der letzte Absatz darf einen bereits deterministisch hinterlegten
  Weekly Focus einordnen, aber keine neue Priorität erfinden.
""".strip()

    response = call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )

    print("\n" + "=" * 80)
    print("RAW HISTORY COACH RESPONSE")
    print(response)
    print("=" * 80 + "\n")

    readiness_summary = _extract_section(
        response,
        "<READINESS_SUMMARY>",
        "</READINESS_SUMMARY>",
    )

    coach_feedback = _extract_section(
        response,
        "<COACH_FEEDBACK>",
        "</COACH_FEEDBACK>",
    )

    if not readiness_summary:
        raise RuntimeError(
            "Readiness-Zusammenfassung konnte nicht aus der "
            "Mistral-Antwort gelesen werden."
        )

    if not coach_feedback:
        raise RuntimeError(
            "Coach-Feedback konnte nicht aus der "
            "Mistral-Antwort gelesen werden."
        )

    return {
        "readiness_summary": readiness_summary,
        "coach_feedback": coach_feedback,
    }

def build_daily_coach_tips(
    *,
    readiness: dict,
    weekly_focus: dict,
    training_analysis: TrainingAnalysis,
    history_summary: dict,
    sportart: str,
    level: str,
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



def _extract_section(
    text: str,
    start_tag: str,
    end_tag: str,
) -> str:
    value = str(text or "").strip()

    start = value.find(start_tag)
    if start == -1:
        return ""

    start += len(start_tag)
    end = value.find(end_tag, start)

    if end == -1:
        return value[start:].strip()

    return value[start:end].strip()

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