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

def _readiness_signal_messages(
    readiness: dict[str, Any],
) -> list[str]:
    """
    Liefert die konkreten Belastungssignale für die
    Readiness-Anzeige.

    Nur Overload-Signale werden hier dargestellt.
    Untertrainingssignale gehören nicht zur aktuellen
    Belastbarkeit.
    """

    signals = readiness.get("overload_signals") or []

    messages: list[str] = []

    for signal in signals:
        if not isinstance(signal, dict):
            continue

        message = str(
            signal.get("message") or ""
        ).strip()

        if message and message not in messages:
            messages.append(message)

    return messages

def render_readiness_card(readiness: dict[str, Any]) -> None:
    """Rendert die aktuelle Belastbarkeit als kompakten Analyse-Status."""
    readiness_display = _readiness_display(readiness)
    readiness_messages = _readiness_signal_messages(readiness)
    status = str(readiness.get("status") or "").strip().casefold()

    summary_line = (
        f'{_safe(readiness_display["icon"])} '
        f'<strong>{_safe(readiness_display["label"])}</strong>'
    )

    if not readiness_messages:
        summary_line += (
            ' <span style="color: var(--text-color-secondary, #667085);">'
            '· '
            f'{_safe(readiness_display["detail"])}'
            '</span>'
        )

    readiness_content = (
        f'<div class="readiness-card {_safe(readiness_display["css_class"])}" '
        'style="padding: 9px 14px; margin-bottom: 10px;">'
        '<div class="muted-label" style="margin: 0 0 3px 0; line-height: 1.15;">'
        'AKTUELLE BELASTBARKEIT'
        '</div>'
        '<div class="readiness-title" style="margin: 0; line-height: 1.35;">'
        f'{summary_line}'
        '</div>'
    )

    if readiness_messages:
        readiness_content += (
            '<ul style="margin: 6px 0 0 22px; padding: 0;">'
            + "".join(
                f'<li style="margin: 2px 0;">{_safe(message)}</li>'
                for message in readiness_messages
            )
            + '</ul>'
        )

        if status == "low":
            readiness_content += (
                '<div class="readiness-detail" style="margin-top: 6px;">'
                'Für die nächsten 24–48 Stunden: Intensität oder Umfang deutlich '
                'reduzieren oder aktive Regeneration nutzen.'
                '</div>'
            )
        elif status in {"moderate", "medium", "caution"}:
            readiness_content += (
                '<div class="readiness-detail" style="margin-top: 6px;">'
                'Beim nächsten geplanten Training Intensität und Umfang bewusst steuern.'
                '</div>'
            )

    readiness_content += "</div>"

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

    feedback = split_coach_feedback(coach_text)

    compact_sections = (
        ("Aktuelle Einordnung", "status"),
        ("Was auffällt", "insights"),
        ("Für die nächsten Einheiten", "next"),
    )

    has_compact_content = any(feedback.get(key, "").strip() for _, key in compact_sections)
    if has_compact_content:
        for title, key in compact_sections:
            content = feedback.get(key, "").strip()
            if content:
                st.markdown(f"#### {title}")
                st.markdown(content)
    else:
        st.markdown("#### Coach-Einordnung")
        coach_summary = feedback.get("summary", "").strip()
        if not coach_summary:
            coach_summary = feedback.get("legacy", "").strip()
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