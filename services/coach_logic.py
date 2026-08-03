from __future__ import annotations

from typing import Any
from services.crossfit_movements import AthleteLevel


def _num(value: object, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _findings(training_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    values = training_analysis.get("top_findings") or training_analysis.get("findings") or []
    return [item for item in values if isinstance(item, dict)]


def build_readiness_summary(
    *,
    history_summary: dict[str, Any],
    training_analysis: dict[str, Any],
) -> dict[str, str]:
    window_7 = (history_summary.get("windows", {}) or {}).get("7_days", {}) or {}
    sessions = int(_num(window_7.get("sessions")))
    avg_rpe = _num(window_7.get("average_rpe"))
    high_rpe = int(_num(window_7.get("high_rpe_sessions")))
    low_rpe = int(_num(window_7.get("low_rpe_sessions")))
    findings = _findings(training_analysis)

    serious = any(
        str(f.get("severity", "")).casefold() in {"high", "critical"}
        and str(f.get("category", "")).casefold() in {"recovery", "training_load"}
        for f in findings
    )
    recovery_codes = {
        "high_density_without_easy_session",
        "limited_recovery_distribution",
        "weekly_load_progression_high",
    }
    recovery_signal = any(str(f.get("code", "")) in recovery_codes for f in findings)

    if serious or (sessions >= 5 and avg_rpe >= 7.8 and low_rpe == 0):
        return {
            "level": "recovery",
            "label": "Regeneration priorisieren",
            "icon": "🔴",
            "css_class": "readiness-recovery",
            "detail": (
                "Die jüngste Trainingsdichte oder Intensität ist erhöht. "
                "Folge deinem Plan heute nur, wenn eine lockere oder regenerative "
                "Einheit vorgesehen ist; einen maximalen Reiz solltest du vermeiden."
            ),
            "plan_guidance": "Bestehenden Plan heute reduzieren oder regenerativ ausführen.",
            "avoid": "Keine zusätzliche hochintensive Einheit ergänzen.",
        }

    if recovery_signal or sessions >= 5 or high_rpe >= 3 or avg_rpe >= 7.2:
        return {
            "level": "caution",
            "label": "Belastung etwas erhöht",
            "icon": "🟡",
            "css_class": "readiness-caution",
            "detail": (
                "Training ist möglich. Halte dich grundsätzlich an dein Programming, "
                "steuere die Intensität aber kontrolliert und verzichte auf unnötige Zusatzbelastung."
            ),
            "plan_guidance": "Programming beibehalten, Intensität bei Bedarf etwas reduzieren.",
            "avoid": "Keinen zweiten harten Reiz an dieselbe Einheit anhängen.",
        }

    return {
        "level": "good",
        "label": "Gut belastbar",
        "icon": "🟢",
        "css_class": "readiness-good",
        "detail": (
            "Die dokumentierte Belastung zeigt aktuell kein klares Warnsignal. "
            "Du kannst deinem bestehenden Plan folgen und nur bei Bedarf gezielt ergänzen."
        ),
        "plan_guidance": "Bestehendem Plan normal folgen.",
        "avoid": "Keine Einschränkung aus den aktuellen Daten ableitbar.",
    }


def _focus_for_text(text: str) -> dict[str, str] | None:
    options = [
        (
            ("vertical_pull", "vertical pull", "vertikales ziehen"),
            "Vertikales Ziehen im Blick behalten",
            "Dieser Bewegungsanteil kam zuletzt vergleichsweise wenig vor. Ergänze ihn nur, wenn dein Programming dafür Spielraum lässt.",
            "Optional nach dem Haupttraining: 3 × 6–10 Klimmzüge, Assisted Pull-ups oder Latziehen · 90 Sek. Pause",
            "missing_component",
        ),
        (
            ("horizontal_pull", "horizontal pull", "horizontales ziehen"),
            "Horizontales Ziehen im Blick behalten",
            "Ruderbewegungen sind aktuell unterrepräsentiert. Ein kurzer Zusatzblock kann sinnvoll sein, ohne das Haupttraining zu ersetzen.",
            "Optional: 3 × 10–12 Ring Rows, Kabelrudern oder Kurzhantelrudern · 75–90 Sek. Pause",
            "missing_component",
        ),
        (
            ("carry", "farmer", "griffkraft"),
            "Carries bei Gelegenheit ergänzen",
            "Tragearbeit und Griffkraft erscheinen im jüngsten Trainingsmix wenig ausgeprägt. Ergänze sie nur passend zum regulären Workout.",
            "Optional: 4 × 40 m Farmers Carry · mittelschwer und technisch sauber",
            "missing_component",
        ),
        (
            ("aerobic_base", "zone 2", "aerobe basis", "locomotion"),
            "Lockere Ausdauer absichern",
            "Die aerobe Grundlage ist im dokumentierten Training wenig vertreten. Nutze eine ohnehin geplante lockere Einheit oder freien Spielraum dafür.",
            "Bei freier Wahl: 30–35 Min. Zone 2 auf Laufband, Bike oder Rower",
            "missing_component",
        ),
        (
            ("threshold", "schwelle"),
            "Kontrollierte Tempoarbeit berücksichtigen",
            "Schwellenarbeit kam zuletzt wenig vor. Sie ist nur dann sinnvoll, wenn dein bestehender Plan eine intensive Ausdauereinheit vorsieht.",
            "Bei passendem Programming: 3 × 6 Min. zügig · 2 Min. locker",
            "missing_component",
        ),
        (
            ("recovery", "regeneration"),
            "Zusätzliche Belastung begrenzen",
            "Die aktuelle Belastungsverteilung spricht gegen einen weiteren harten Zusatzreiz. Folge einem lockeren Programmtag oder reduziere die Einheit.",
            "Bei freier Wahl: 20–30 Min. sehr locker, Mobilität oder vollständiger Ruhetag",
            "load_adjustment",
        ),
        (
            ("mobility", "mobilität"),
            "Mobilität als kleinen Zusatz nutzen",
            "Mobilitätsarbeit kann den bestehenden Plan ergänzen, ohne einen eigenständigen Trainingstag zu erzeugen.",
            "Optional: 8–10 Min. für die im Workout beanspruchten Bereiche",
            "small_add_on",
        ),
    ]
    for keys, title, body, session, mode in options:
        if any(key in text for key in keys):
            return {
                "title": title,
                "text": body,
                "session": session,
                "mode": mode,
            }
    return None


def build_weekly_focus(
    *,
    training_analysis: dict[str, Any],
    primary_goal: str,
    training_balance: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return one supporting priority, never a weekly training plan."""
    findings = _findings(training_analysis)
    crossfit_focus = build_crossfit_focus(
        history_summary=training_analysis.get(
            "history_summary",
            {}
        )
    )

    if crossfit_focus is not None:
        return crossfit_focus
    if training_balance:
        findings.extend(
            item
            for item in (training_balance.get("findings", []) or [])
            if isinstance(item, dict)
        )

    for finding in findings:
        text = " ".join(
            str(finding.get(key, ""))
            for key in (
                "code",
                "key",
                "title",
                "recommendation",
                "description",
                "text",
            )
        ).casefold()
        focus = _focus_for_text(text)
        if focus:
            return focus

    fallbacks = {
        "Hyrox": {
            "title": "Programming zielgerichtet ergänzen",
            "text": (
                "Dein Verlauf zeigt keinen eindeutig fehlenden Schwerpunkt. Folge deinem Plan; "
                "bei freier Wahl ist eine kleine Kombination aus lockerer Ausdauer und Stationsqualität passend."
            ),
            "session": "Optional: 20–30 Min. Zone 2 oder 3 × 40 m Farmers Carry",
            "mode": "optional",
        },
        "CrossFit": {
            "title": "Programming ausgewogen umsetzen",
            "text": (
                "Es liegt kein klarer Mangel vor. Folge dem Gym-Programming und ergänze höchstens "
                "einen kurzen Zug-, Rumpf- oder lockeren Ausdauerblock."
            ),
            "session": "Optional: 3 saubere Zusatzsätze oder 15–20 Min. lockeres Bike",
            "mode": "optional",
        },
        "Laufen": {
            "title": "Laufplan unterstützen",
            "text": (
                "Der Laufplan bleibt die Hauptsteuerung. Ergänze nur kurze Laufkraft- oder "
                "Mobilitätsarbeit, sofern die geplante Belastung dadurch nicht verändert wird."
            ),
            "session": "Optional: 3 × 12–15 Calf Raises je Seite + 6–8 Min. Rumpf",
            "mode": "optional",
        },
    }
    return fallbacks.get(
        primary_goal,
        {
            "title": "Bestehenden Rhythmus unterstützen",
            "text": (
                "Aktuell ist keine klare Korrektur nötig. Folge deinem Plan und nutze Ergänzungen "
                "nur klein, gezielt und passend zur vorgesehenen Einheit."
            ),
            "session": "Optional: 10–20 Min. lockere Bewegung oder 2–3 saubere Zusatzsätze",
            "mode": "optional",
        },
    )


def build_positive_observations(
    *,
    history_summary: dict[str, Any],
    training_analysis: dict[str, Any],
) -> list[str]:
    windows = history_summary.get("windows", {}) or {}
    w7 = windows.get("7_days", {}) or {}
    w28 = windows.get("28_days", {}) or {}
    sessions_7 = int(_num(w7.get("sessions")))
    sessions_28 = int(_num(w28.get("sessions")))
    positives: list[str] = []

    if sessions_28 >= 8:
        positives.append(f"Starke Trainingskontinuität mit {sessions_28} Einheiten in den letzten 28 Tagen.")
    elif sessions_28 >= 4:
        positives.append(f"Solide Trainingsroutine mit {sessions_28} Einheiten in den letzten 28 Tagen.")

    if sum(_num(v) > 0 for v in (w28.get("training_goal_counts", {}) or {}).values()) >= 4:
        positives.append("Dein tatsächlich absolviertes Training deckt mehrere Trainingsziele ab.")

    if sum(_num(v) > 0 for v in (w28.get("movement_pattern_load", {}) or {}).values()) >= 5:
        positives.append("Mehrere Bewegungsmuster sind im dokumentierten Training regelmäßig vertreten.")

    if sessions_7 and int(_num(w7.get("low_rpe_sessions"))) > 0:
        positives.append("Mindestens eine lockere Einheit verbessert die Belastungsverteilung der letzten sieben Tage.")

    if not positives:
        positives.append("Die strukturierte Erfassung macht Abweichungen vom geplanten Training zunehmend sichtbar.")

    return positives[:3]

def build_crossfit_focus(
    *,
    history_summary: dict[str, Any],
) -> dict[str, str] | None:
    """
    Erstellt einen sportartspezifischen CrossFit-Hinweis
    auf Basis der Movement-Coverage.
    """

    coverage = history_summary.get(
        "crossfit_coverage",
        {}
    )

    missing = history_summary.get(
        "missing_crossfit_movements",
        []
    )

    if not coverage:
        return None

    percentage = float(
        coverage.get(
            "coverage_percent",
            100.0,
        )
    )

    athlete_level = coverage.get(
        "athlete_level",
        "scaled",
    )

    if percentage >= 90:
        return {
            "title": "Sehr ausgewogene CrossFit-Abdeckung",
            "text": (
                "Nahezu alle für dein Level relevanten "
                "Movement Families wurden in den letzten "
                "Wochen trainiert."
            ),
            "session": (
                "Keine gezielte Ergänzung notwendig."
            ),
            "mode": "balanced",
        }

    if missing:

        movement = (
            missing[0]
            .replace("_", " ")
            .title()
        )

        return {
            "title": (
                "Fehlendes CrossFit-Movement"
            ),
            "text": (
                f"Für dein {athlete_level.title()}-Level "
                f"fehlt aktuell '{movement}'."
            ),
            "session": (
                "Wenn dein Programming es zulässt, "
                "ergänze in einer der nächsten Wochen "
                "einen Technikblock."
            ),
            "mode": "crossfit",
        }

    return None