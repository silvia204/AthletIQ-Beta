from __future__ import annotations

import html
from typing import Any

import streamlit as st

from analyzers.history import readiness


def split_coach_feedback(text: str) -> dict[str, str]:
    """Trennt kompakte Coachtexte; ältere gespeicherte Formate bleiben lesbar."""
    aliases = {
        "aktuelle einordnung": "status",
        "dein aktueller trainingsstatus": "status",
        "trainingsstatus": "status",
        "was auffällt": "insights",
        "was auffaellt": "insights",
        "für die nächsten einheiten": "next",
        "fuer die naechsten einheiten": "next",
        "bewegungsmuster": "legacy",
        "muskelgruppen": "legacy",
        "trainingsziele": "legacy",
        "belastungsarten": "legacy",
        "crossfit-movements": "legacy",
        "crossfit movements": "legacy",
        "coach-einordnung": "summary",
        "coach einordnung": "summary",
        "coach-zusammenfassung": "summary",
        "coach zusammenfassung": "summary",
        "deine entwicklung": "summary",
    }
    buffers = {key: [] for key in ("status", "insights", "next", "legacy", "summary")}
    current = "summary"
    for raw in str(text or "").splitlines():
        normalized = raw.strip().lstrip("#").strip().rstrip(":").casefold()
        if normalized in aliases:
            current = aliases[normalized]
        else:
            buffers[current].append(raw)
    return {key: "\n".join(lines).strip() for key, lines in buffers.items()}

def _safe(value: object, fallback: str = "") -> str:
    return html.escape(
        str(value if value not in (None, "") else fallback)
    )

def _readiness_display(
    readiness: dict[str, Any],
) -> dict[str, str]:
    """
    Übersetzt den fachlichen Readiness-Status in die
    Darstellung des Coach-Dashboards.

    Der Status aus der Analyse ist die Single Source of Truth.
    Fehlende UI-Felder dürfen niemals automatisch als
    'gut belastbar' interpretiert werden.
    """

    status = str(
        readiness.get("status") or ""
    ).strip().casefold()

    warning_count = int(
        readiness.get("warning_count", 0) or 0
    )

    if status == "low":
        return {
            "css_class": "readiness-warning",
            "icon": "🔴",
            "label": "Belastbarkeit aktuell reduziert",
            "detail": (
                f"Es wurden {warning_count} relevante "
                "Belastungswarnungen erkannt."
                if warning_count
                else
                "Mehrere relevante Belastungssignale wurden erkannt."
            ),
            "plan_guidance": (
                "Wenn innerhalb der nächsten 24–48 Stunden eine Einheit geplant ist, "
                "reduziere Intensität oder Umfang deutlich. Alternativ kann eine leichte "
                "aktive Regeneration sinnvoll sein."
            ),
        }

    if status in {"moderate", "medium", "caution"}:
        return {
            "css_class": "readiness-moderate",
            "icon": "🟡",
            "label": "Belastbarkeit beobachten",
            "detail": (
                "Es liegen Belastungssignale vor, die du bei "
                "deinem nächsten geplanten Training berücksichtigen solltest."
            ),
            "plan_guidance": (
                "Dein geplantes Training kann grundsätzlich "
                "bestehen bleiben. Passe Intensität oder Umfang "
                "an, wenn die Belastung höher als vorgesehen ausfällt."
            ),
        }

    if status == "high":
        return {
            "css_class": "readiness-good",
            "icon": "🟢",
            "label": "Gut belastbar",
            "detail": (
                "Aktuell wurden keine relevanten "
                "Überlastungswarnungen erkannt."
            ),
            "plan_guidance": (
                "Dein geplantes Training kann grundsätzlich "
                "wie vorgesehen stattfinden."
            ),
        }

    return {
        "css_class": "readiness-neutral",
        "icon": "⚪",
        "label": "Belastbarkeit noch nicht eindeutig",
        "detail": (
            "Die aktuelle Datenlage reicht für eine eindeutige "
            "Belastungseinschätzung noch nicht aus."
        ),
        "plan_guidance": (
            "Orientiere dich an deinem bestehenden Plan und "
            "beurteile die Belastung konservativ."
        ),
    }

def _readiness_signal_groups(
    readiness: dict[str, Any],
) -> dict[str, list[str]]:
    """Gruppiert Readiness-Signale für eine kompakte, ursachenbezogene Anzeige."""
    signals = readiness.get("overload_signals") or []

    load_type_labels = {
        "high_mechanical_load": "Mechanisch",
        "high_eccentric_load": "Exzentrisch",
        "high_impact_load": "Impact",
        "high_neuromuscular_load": "Neuromuskulär",
    }
    muscle_labels = {
        "quadriceps": "Quadrizeps",
        "hamstrings": "Hamstrings",
        "calves": "Waden",
        "glutes": "Glutes",
        "chest": "Brust",
        "back": "Rücken",
        "shoulders": "Schultern",
        "biceps": "Bizeps",
        "triceps": "Trizeps",
        "core": "Core",
    }

    warnings: list[str] = []
    load_types: list[str] = []
    muscles: list[str] = []
    other_notices: list[str] = []

    for signal in signals:
        if not isinstance(signal, dict):
            continue

        code = str(signal.get("code") or "").strip()
        severity = str(signal.get("severity") or "").strip().casefold()
        message = str(signal.get("message") or "").strip()

        if severity == "warning":
            if message and message not in warnings:
                warnings.append(message)
            continue

        if code in load_type_labels:
            label = load_type_labels[code]
            if label not in load_types:
                load_types.append(label)
            continue

        if code.startswith("high_recent_"):
            muscle_key = code.removeprefix("high_recent_")
            label = muscle_labels.get(
                muscle_key,
                muscle_key.replace("_", " ").title(),
            )
            if label not in muscles:
                muscles.append(label)
            continue

        if message and message not in other_notices:
            other_notices.append(message)

    return {
        "warnings": warnings,
        "load_types": load_types,
        "muscles": muscles,
        "other_notices": other_notices,
    }


def render_readiness_card(readiness: dict[str, Any]) -> None:
    """Rendert die aktuelle Belastbarkeit kompakt und erklärt den Statusauslöser."""
    readiness_display = _readiness_display(readiness)
    signal_groups = _readiness_signal_groups(readiness)
    status = str(readiness.get("status") or "").strip().casefold()
    status_reason = str(readiness.get("status_reason") or "").strip().casefold()

    summary_line = (
        f'{_safe(readiness_display["icon"])} '
        f'<strong>{_safe(readiness_display["label"])}</strong>'
    )

    detail = readiness_display["detail"]
    if status_reason == "local_load_accumulation":
        detail = (
            "Mehrere lokale Belastungssignale treten gleichzeitig auf. "
            "Die Gesamtbelastung ist damit nicht zwingend zu hoch, einzelne Bereiche "
            "waren zuletzt aber wiederholt stärker gefordert."
        )

    readiness_content = (
        f'<div class="readiness-card {_safe(readiness_display["css_class"])}" '
        'style="padding: 10px 14px; margin-bottom: 10px;">'
        '<div class="muted-label" style="margin: 0 0 3px 0; line-height: 1.15;">'
        'AKTUELLE BELASTBARKEIT'
        '</div>'
        '<div class="readiness-title" style="margin: 0; line-height: 1.35;">'
        f'{summary_line}'
        '</div>'
        '<div class="readiness-detail" style="margin-top: 5px;">'
        f'{_safe(detail)}'
        '</div>'
    )

    if signal_groups["warnings"]:
        readiness_content += (
            '<div style="margin-top: 7px;"><strong>Relevante Warnsignale:</strong></div>'
            '<ul style="margin: 4px 0 0 22px; padding: 0;">'
            + "".join(
                f'<li style="margin: 2px 0;">{_safe(message)}</li>'
                for message in signal_groups["warnings"]
            )
            + '</ul>'
        )

    if signal_groups["load_types"]:
        readiness_content += (
            '<div class="readiness-detail" style="margin-top: 7px;">'
            '<strong>Belastungsarten:</strong> '
            + _safe(" · ".join(signal_groups["load_types"]))
            + '</div>'
        )

    if signal_groups["muscles"]:
        readiness_content += (
            '<div class="readiness-detail" style="margin-top: 3px;">'
            '<strong>Stärker beansprucht:</strong> '
            + _safe(" · ".join(signal_groups["muscles"]))
            + '</div>'
        )

    if signal_groups["other_notices"] and not (
        signal_groups["load_types"] or signal_groups["muscles"]
    ):
        readiness_content += (
            '<ul style="margin: 6px 0 0 22px; padding: 0;">'
            + "".join(
                f'<li style="margin: 2px 0;">{_safe(message)}</li>'
                for message in signal_groups["other_notices"]
            )
            + '</ul>'
        )

    if status == "low":
        guidance = (
            "Für die nächsten 24–48 Stunden Intensität oder Umfang deutlich reduzieren; "
            "alternativ leichte aktive Regeneration nutzen."
        )
    elif status in {"moderate", "medium", "caution"}:
        guidance = (
            "Beim nächsten geplanten Training Intensität und Umfang bewusst steuern "
            "und die zuletzt stärker beanspruchten Bereiche berücksichtigen."
        )
    else:
        guidance = readiness_display["plan_guidance"]

    readiness_content += (
        '<div class="readiness-detail" style="margin-top: 8px;">'
        f'<strong>Nächstes Training:</strong> {_safe(guidance)}'
        '</div>'
        '</div>'
    )

    st.markdown(readiness_content, unsafe_allow_html=True)

def render_coach_dashboard(
    *,
    user_name: str,
    user_sport: str,
    user_level: str,
    sessions_28: int,
    readiness: dict[str, str],
    positive_observations: list[str],
    weekly_focus: dict[str, str],
    coach_text: str,
    daily_coach_tips: dict[str, str],
    load_trend: dict[str, Any],
    consistency: dict[str, Any],
    diversity: dict[str, Any],
) -> None:
    """
    Rendert den Tab 'Einordnung'.

    Wichtig:
    Einige Parameter werden aktuell bewusst nicht mehr direkt
    dargestellt. Sie bleiben vorerst in der Signatur, damit
    bestehende Aufrufer nicht angepasst werden müssen.
    """

    # ----------------------------------------------------
    # EINORDNUNG
    # ----------------------------------------------------

    st.markdown("### Einordnung")

    st.caption(
        "Dein Coach ordnet dein absolviertes Training im Kontext "
        "deiner bisherigen Entwicklung ein und zeigt dir, was für "
        "dein nächstes geplantes Training relevant ist."
    )

    # ----------------------------------------------------
    # COACH-EINORDNUNG
    # ----------------------------------------------------

    coach_summary = str(coach_text or "").strip()
    if coach_summary:
        st.markdown(coach_summary)
    else:
        st.caption(
            "Für eine ausführliche Coach-Einordnung liegen aktuell "
            "noch nicht genügend Informationen vor."
        )

    # ----------------------------------------------------
    # NÄCHSTES GEPLANTES TRAINING
    # ----------------------------------------------------

    # ----------------------------------------------------
    # ERKLÄRUNG
    # ----------------------------------------------------

    with st.expander("Wie kommt die Einordnung zustande?"):
        st.markdown(
            "Die App betrachtet dein tatsächlich absolviertes "
            "Training im Zusammenhang mit deiner bisherigen "
            "Trainingshistorie. Dabei werden unter anderem "
            "Belastungsverteilung, wiederkehrende Schwerpunkte, "
            "Trainingsvielfalt und erkennbare Lücken berücksichtigt. "
            "Die Einordnung ersetzt keinen Trainingsplan. Sie soll "
            "dir helfen, dein bestehendes Programming sinnvoll "
            "einzuordnen und bei Bedarf gezielt zu ergänzen."
        )