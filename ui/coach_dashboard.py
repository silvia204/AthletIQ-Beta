from __future__ import annotations

import html
from typing import Any

import streamlit as st

from analyzers.history import readiness


def split_coach_feedback(text: str) -> dict[str, str]:
    """
    Trennt den von Mistral erzeugten Coachtext in:
    - Coach-Einordnung
    - Empfehlung für das nächste Training

    Ältere Überschriften bleiben als Aliase erhalten,
    damit bereits erzeugte Texte weiterhin funktionieren.
    """
    aliases = {
        "coach-einordnung": "summary",
        "coach einordnung": "summary",
        "coach-zusammenfassung": "summary",
        "coach zusammenfassung": "summary",
        "deine entwicklung": "summary",
        "empfehlung für dein nächstes training": "next_session",
        "empfehlung für die nächste einheit": "next_session",
        "nächste einheit": "next_session",
    }

    buffers = {
        "summary": [],
        "next_session": [],
    }
    current = "summary"

    for raw in str(text or "").splitlines():
        normalized = (
            raw.strip()
            .lstrip("#")
            .strip()
            .rstrip(":")
            .casefold()
        )

        if normalized in aliases:
            current = aliases[normalized]
        else:
            buffers[current].append(raw)

    return {
        key: "\n".join(lines).strip()
        for key, lines in buffers.items()
    }

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

    readiness_display = _readiness_display(readiness)
    readiness_messages = _readiness_signal_messages(readiness)

    # ----------------------------------------------------
    # HEADER
    # ----------------------------------------------------

    st.markdown(
        (
            '<div class="welcome-card">'
            f'<div class="welcome-title">'
            f'Willkommen zurück, {_safe(user_name, "Athlet")}'
            '</div>'
            f'<div>{_safe(user_sport, "Sport")} &nbsp;·&nbsp; '
            f'{_safe(user_level, "Level")} &nbsp;·&nbsp; '
            f'{int(sessions_28 or 0)} Workouts in 28 Tagen</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### Einordnung")

    st.caption(
        "Dein Coach ordnet dein absolviertes Training im Kontext "
        "deiner bisherigen Entwicklung ein und zeigt dir, was für "
        "dein nächstes geplantes Training relevant ist."
    )

    # ----------------------------------------------------
    # AKTUELLE BELASTBARKEIT
    # ----------------------------------------------------

    status = str(
        readiness.get("status") or ""
    ).strip().casefold()

    readiness_content = (
        f'<div class="readiness-card '
        f'{_safe(readiness_display["css_class"])}">'
        '<div class="muted-label">'
        'AKTUELLE BELASTBARKEIT'
        '</div>'
        '<div class="readiness-title">'
        f'{_safe(readiness_display["icon"])} '
        f'{_safe(readiness_display["label"])}'
        '</div>'
    )

    # Konkrete Gründe anzeigen
    if readiness_messages:
        readiness_content += (
            '<div class="readiness-detail" '
            'style="margin-top: 14px;">'
            'Deine aktuelle Trainingshistorie zeigt:'
            '</div>'
            '<ul style="margin-top: 8px; margin-bottom: 0;">'
        )

        for message in readiness_messages:
            readiness_content += (
                f'<li>{_safe(message)}</li>'
            )

        readiness_content += "</ul>"

    else:
        readiness_content += (
            '<div class="readiness-detail" '
            'style="margin-top: 14px;">'
            f'{_safe(readiness_display["detail"])}'
            '</div>'
        )

    # Kurzfristige Konsequenz nur bei reduzierter
    # oder eingeschränkter Belastbarkeit
    if status == "low":
        readiness_content += (
            '<div class="muted-label" '
            'style="margin-top: 20px;">'
            'FÜR DIE NÄCHSTEN 24–48 STUNDEN'
            '</div>'
            '<div class="readiness-detail" '
            'style="margin-top: 6px;">'
            'Wenn Training geplant ist, reduziere Intensität '
            'oder Umfang deutlich oder nutze aktive Regeneration. '
            'Liegt dein nächstes Training später, beurteile deine '
            'Belastbarkeit zu diesem Zeitpunkt erneut.'
            '</div>'
        )

    elif status in {"moderate", "medium", "caution"}:
        readiness_content += (
            '<div class="muted-label" '
            'style="margin-top: 20px;">'
            'FÜR DIE NÄCHSTEN 24–48 STUNDEN'
            '</div>'
            '<div class="readiness-detail" '
            'style="margin-top: 6px;">'
            'Wenn Training geplant ist, steuere Intensität und '
            'Umfang bewusst und berücksichtige die genannten '
            'Belastungssignale.'
            '</div>'
        )

    readiness_content += "</div>"

    st.markdown(
        readiness_content,
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------
    # COACH-EINORDNUNG
    # ----------------------------------------------------

    feedback = split_coach_feedback(coach_text)

    coach_summary = feedback.get("summary", "").strip()
    next_session = feedback.get("next_session", "").strip()

    st.markdown("#### Coach-Einordnung")

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