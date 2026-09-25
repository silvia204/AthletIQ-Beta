"""
mistral_coach.py

Erstellt das finale Coach-Feedback mit Mistral.

Diese Schicht enthält ausschließlich
Prompt Building und den LLM-Aufruf.
"""

from __future__ import annotations

import json
import re

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
    """Verdichtet deterministische Analysefakten zu einer zusammenhängenden Coach-Einordnung."""
    readiness_facts = coach_context.get("readiness_summary_facts", {})
    history_facts = coach_context.get("history_coach_facts", {})

    prompt = f"""
{COACH_PROMPT}

SPORTART: {sportart}
LEVEL: {level}
BESCHWERDEN: {injuries or "Keine"}

DETERMINISTISCHE COACH-FAKTEN
{json.dumps(history_facts, ensure_ascii=False, indent=2)}

READINESS-KURZFAKTEN
{json.dumps(readiness_facts, ensure_ascii=False, indent=2)}

AUFGABE
Schreibe eine zusammenhängende Coach-Einordnung zum dokumentierten Training.
Der Text soll die aktuelle Situation, die wichtigsten strukturellen Auffälligkeiten und die
praktische Bedeutung für das nächste geplante Training sinnvoll miteinander verbinden.

WICHTIG:
- Schreibe EINEN kohärenten Coachtext ohne Zwischenüberschriften oder künstliche Sektionen.
- 2 bis 3 kurze Absätze sind erlaubt, wenn sie den Lesefluss verbessern.
- Wiederhole keine Aussage oder Begründung innerhalb des Textes.
- Bewegungsmuster, Muskelgruppen, Trainingsziele und Belastungsarten NICHT einzeln abarbeiten.
- CrossFit-Movements oder CrossFit-Standards nur dann erwähnen, wenn SPORTART ausdrücklich
  CrossFit ist und entsprechende CrossFit-Fakten im Faktenblock vorhanden sind. Bei HYROX
  CrossFit niemals als Benchmark, Vergleichsstandard oder Referenz verwenden.
- Führe zusammengehörige Signale zu EINEM Coaching-Punkt zusammen.
- Nenne nur die 1 bis maximal 3 relevantesten Auffälligkeiten insgesamt.
- Keine vollständige Bestandsaufnahme und keine Wiederholung der Analysewerte.
- Keine internen Feldnamen, snake_case-Begriffe oder technischen Codes.
- Erfinde keine Lücken. Muskelgruppen nur anhand von muscle_group_target_assessment bewerten.
- Erfinde keine Trainingsqualitäten oder Fachbegriffe. Verwende nur Trainingsziele,
  Bewegungsmuster und Belastungsarten, die in den deterministischen Fakten vorkommen.
- Maximalkraft und Kraftausdauer getrennt behandeln; niemals "maximale Kraftausdauer" formulieren.
- Technik, technische Präzision, Mobilität oder ähnliche Lücken nur nennen, wenn sie als
  deterministischer Fakt ausdrücklich vorhanden sind.
- Movement-Recency ist keine Trainingspause.
- Historische Aussagen immer auf den dokumentierten Analysezeitraum beziehen.
- Keine medizinischen, biomechanischen oder leistungsbezogenen Kausalbehauptungen ableiten,
  die nicht ausdrücklich in den deterministischen Fakten stehen.
- Begriffe wie "überrepräsentiert" nur verwenden, wenn der deterministische Zielbereich
  tatsächlich den Status "over" liefert.

READINESS UND TRAININGSRECENCY HABEN HÖCHSTE PRIORITÄT:
- Wenn seit der letzten dokumentierten Einheit >= 7 Tage vergangen sind, steht zunächst ein
  kontrollierter Wiedereinstieg im Vordergrund. Historische Lücken dürfen genannt werden,
  aber nicht als sofort abzuarbeitende Zusatzreize.
- low: Regeneration/sehr leichte Aktivität; keine Zusatzreize.
- moderate/medium/caution: Belastung steuern; Lücken nur als späteres Thema.
- high: Ohne längere Trainingspause darf bei einer echten relevanten Lücke eine kleine konkrete
  Ergänzung mit höchstens 1–2 einfachen Übungsbeispielen genannt werden.
- Ein zusätzlicher Trainingsblock ist nicht automatisch nötig.

LÄNGE UND STIL:
- Ideal 100–160 Wörter, niemals mehr als 190 Wörter.
- Präzise, coachend und konkret; keine Floskeln.
- Ausschließlich Klartext: kein Markdown, keine Sternchen, keine Listenmarker, keine Überschriften.

AUSGABEFORMAT – exakt diese zwei Tags und immer mit schließendem Tag:
<READINESS_SUMMARY>Ein kurzer Satz nur zu Overload-Signalen.</READINESS_SUMMARY>
<COACH_FEEDBACK>Der vollständige zusammenhängende Coachtext.</COACH_FEEDBACK>

Nichts vor oder nach diesen Tags ausgeben.
""".strip()

    response = call_mistral(api_key=api_key, model=model, content=prompt)

    readiness_summary = _sanitize_coach_text(
        _extract_section(response, "<READINESS_SUMMARY>", "</READINESS_SUMMARY>")
    )
    coach_feedback = _sanitize_coach_text(
        _extract_section(response, "<COACH_FEEDBACK>", "</COACH_FEEDBACK>")
    )

    if not readiness_summary or not coach_feedback:
        raise RuntimeError(
            "Coach-Einordnung konnte nicht vollständig aus der Mistral-Antwort gelesen werden."
        )

    return {"readiness_summary": readiness_summary, "coach_feedback": coach_feedback}

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



def _sanitize_coach_text(text: str) -> str:
    """Bereinigt LLM-Steuer-Tags und unerwünschtes Markdown aus Coachtexten."""
    value = str(text or "").strip()

    # Alle bekannten Abschnittstags entfernen, auch wenn Mistral sie verschachtelt
    # oder ein schließendes Tag an der falschen Stelle ausgibt.
    value = re.sub(
        r"</?(?:READINESS_SUMMARY|COACH_FEEDBACK|STATUS|INSIGHTS|NEXT)>",
        "",
        value,
        flags=re.IGNORECASE,
    )

    cleaned_lines: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        # Coachtext wird als Klartext gespeichert; die UI formatiert die Abschnitte.
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = line.replace("**", "").replace("__", "")
        line = line.replace("`", "")
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


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