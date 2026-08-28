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
    """Verdichtet deterministische Analysefakten zu wenigen Coaching-Erkenntnissen."""
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
Schreibe eine sehr kompakte Coach-Einordnung. Die Analyse ist im Hintergrund detailliert;
hier sollen nur die wichtigsten Erkenntnisse erscheinen.

WICHTIG:
- Bewegungsmuster, Muskelgruppen, Trainingsziele, Belastungsarten und CrossFit-Movements
  NICHT einzeln abarbeiten.
- Führe zusammengehörige Signale zu EINEM Coaching-Punkt zusammen.
  Beispiel: wenig horizontales Drücken + Brust unter Zielbereich = ein gemeinsamer Punkt.
- Nenne nur 1 bis maximal 3 relevante Auffälligkeiten insgesamt.
- Wenn mehrere Kategorien dieselbe Ursache beschreiben, erwähne sie nicht doppelt.
- Wenn eine Kategorie keinen zusätzlichen Erkenntnisgewinn liefert, lasse sie vollständig weg.
- Keine vollständige Bestandsaufnahme und keine Wiederholung der Analysewerte.
- Keine internen Feldnamen, snake_case-Begriffe oder technischen Codes.
- Erfinde keine Lücken. Muskelgruppen nur anhand von muscle_group_target_assessment bewerten.
- Movement-Recency ist keine Trainingspause.
- Formuliere historische Aussagen immer bezogen auf den dokumentierten Analysezeitraum:
  statt „nie trainiert“ z. B. „im betrachteten Zeitraum nicht dokumentiert“.
- Keine medizinischen, biomechanischen oder leistungsbezogenen Kausalbehauptungen ableiten,
  die nicht ausdrücklich in den deterministischen Fakten stehen. Insbesondere nicht behaupten,
  dass eine Verteilung Schulterstabilität, Leistungsfähigkeit oder Verletzungsrisiko einschränkt.
- Begriffe wie „überrepräsentiert“ nur verwenden, wenn der entsprechende deterministische
  Zielbereich tatsächlich den Status „over“ liefert.
- Priorisiere: Lieber 1–2 wirklich relevante Erkenntnisse als mehrere schwächere Signale.

READINESS UND TRAININGSRECENCY HABEN HÖCHSTE PRIORITÄT:
- Wenn seit der letzten dokumentierten Einheit >= 7 Tage vergangen sind, steht zunächst ein
  kontrollierter Wiedereinstieg im Vordergrund. Historische Lücken dürfen genannt werden,
  aber nicht als sofort abzuarbeitende Zusatzreize.
- Bei >= 7 Tagen Pause keine Formulierung wie „die Pause bietet die Chance, Lücken zu schließen“.
- low: Regeneration/sehr leichte Aktivität; keine Zusatzreize.
- moderate/medium/caution: Belastung steuern; Lücken nur als späteres Thema, kein Zusatzblock.
- high: Ohne längere Trainingspause darf bei einer echten relevanten Lücke eine kleine konkrete
  Ergänzung mit höchstens 1–2 einfachen Übungsbeispielen genannt werden.
- high nach >= 7 Tagen ohne dokumentierte Einheit bedeutet nicht automatisch Zusatztraining:
  zuerst kontrollierter Wiedereinstieg, danach schrittweise Integration relevanter Lücken.
- Ein zusätzlicher Trainingsblock ist nicht automatisch nötig.

LÄNGE:
- STATUS: maximal 2 kurze Sätze.
- INSIGHTS: maximal 3 kurze Absätze; jeder Absatz maximal 2 Sätze.
- NEXT: maximal 2 kurze Sätze. Wenn keine konkrete Handlung nötig ist, sage das knapp.
- Gesamter Coachtext idealerweise 120–180 Wörter, niemals mehr als 220 Wörter.

AUSGABEFORMAT – exakt diese Tags und immer mit schließendem Tag:
<READINESS_SUMMARY>Ein kurzer Satz nur zu Overload-Signalen.</READINESS_SUMMARY>
<STATUS>Maximal zwei kurze Sätze zu Trainingsrhythmus, letzter Einheit und Readiness.</STATUS>
<INSIGHTS>Ein bis maximal drei kurze Absätze mit den wichtigsten zusammengeführten Erkenntnissen.</INSIGHTS>
<NEXT>Eine kurze koordinierte Konsequenz für die nächsten Einheiten oder der Hinweis, dass aktuell keine gezielte Ergänzung nötig ist.</NEXT>

Nichts vor oder nach diesen Tags ausgeben.
""".strip()

    response = call_mistral(api_key=api_key, model=model, content=prompt)

    readiness_summary = _extract_section(response, "<READINESS_SUMMARY>", "</READINESS_SUMMARY>")
    status = _extract_section(response, "<STATUS>", "</STATUS>")
    insights = _extract_section(response, "<INSIGHTS>", "</INSIGHTS>")
    next_step = _extract_section(response, "<NEXT>", "</NEXT>")

    # Robustheit gegen fehlerhafte/fehlende schließende Tags von Mistral:
    # Kein Folgeabschnitt darf in den vorherigen Abschnitt hineinlaufen.
    if "<NEXT>" in insights:
        insights = insights.split("<NEXT>", 1)[0].strip()
    for tag in ("<INSIGHTS>", "<NEXT>"):
        if tag in status:
            status = status.split(tag, 1)[0].strip()
    for tag in ("<STATUS>", "<INSIGHTS>", "<NEXT>"):
        if tag in readiness_summary:
            readiness_summary = readiness_summary.split(tag, 1)[0].strip()

    if not readiness_summary or not status or not insights or not next_step:
        raise RuntimeError(
            "Kompakte Coach-Einordnung konnte nicht vollständig aus der Mistral-Antwort gelesen werden."
        )

    coach_feedback = (
        f"## Aktuelle Einordnung\n{status}\n\n"
        f"## Was auffällt\n{insights}\n\n"
        f"## Für die nächsten Einheiten\n{next_step}"
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