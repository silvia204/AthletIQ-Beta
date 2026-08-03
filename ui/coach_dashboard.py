from __future__ import annotations

import html
from typing import Any

import streamlit as st


def split_coach_feedback(text: str) -> dict[str, str]:
    aliases = {
        "coach-zusammenfassung": "summary",
        "coach zusammenfassung": "summary",
        "deine entwicklung": "summary",
        "empfehlung für dein nächstes training": "next_session",
        "empfehlung für die nächste einheit": "next_session",
        "nächste einheit": "next_session",
    }
    buffers = {"summary": [], "next_session": []}
    current = "summary"

    for raw in str(text or "").splitlines():
        normalized = raw.strip().lstrip("#").strip().rstrip(":").casefold()
        if normalized in aliases:
            current = aliases[normalized]
        else:
            buffers[current].append(raw)

    return {key: "\n".join(lines).strip() for key, lines in buffers.items()}


def _safe(value: object, fallback: str = "") -> str:
    return html.escape(str(value if value not in (None, "") else fallback))


def _metric_delta(value: object, suffix: str = "") -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value):+.1f}{suffix}"
    except (TypeError, ValueError):
        return None


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
    load_trend: dict[str, Any],
    consistency: dict[str, Any],
    diversity: dict[str, Any],
) -> None:
    st.markdown(
        (
            '<div class="welcome-card">'
            f'<div class="welcome-title">Willkommen zurück, {_safe(user_name, "Athlet")}</div>'
            f'<div>{_safe(user_sport, "Sport")} &nbsp;·&nbsp; '
            f'{_safe(user_level, "Level")} &nbsp;·&nbsp; '
            f'{int(sessions_28 or 0)} Workouts in 28 Tagen</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### Mein Trainings-Co-Pilot")
    st.caption(
        "Einordnung deines tatsächlich absolvierten Trainings – als Ergänzung zu deinem bestehenden Plan oder Gym-Programming."
    )

    st.markdown(
        (
            f'<div class="readiness-card {_safe(readiness.get("css_class"), "readiness-good")}">'
            '<div class="muted-label">AKTUELLE BELASTBARKEIT</div>'
            f'<div class="readiness-title">{_safe(readiness.get("icon"), "🟢")} '
            f'{_safe(readiness.get("label"), "Trainingsstatus")}</div>'
            f'<div>{_safe(readiness.get("detail"))}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("#### Entscheidung für das nächste geplante Training")
    guidance_left, guidance_right = st.columns([1.15, 1], gap="large")

    with guidance_left:
        with st.container(border=True):
            st.markdown("##### Umgang mit deinem Plan")
            st.markdown(
                readiness.get("plan_guidance")
                or "Folge grundsätzlich deinem bestehenden Trainingsplan."
            )
            avoid = readiness.get("avoid")
            if avoid:
                st.markdown(f"**Aktuell vermeiden:** {avoid}")

    with guidance_right:
        st.markdown(
            (
                '<div class="focus-card">'
                '<div class="muted-label">RELEVANTE ERGÄNZUNG</div>'
                f'<div class="readiness-title">{_safe(weekly_focus.get("title"), "Aktueller Fokus")}</div>'
                f'<div>{_safe(weekly_focus.get("text"))}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    sections = split_coach_feedback(coach_text)

    st.markdown("#### Coach-Einordnung")
    with st.container(border=True):
        st.markdown(
            sections["summary"]
            or "Mit weiteren gespeicherten Einheiten kann ich Abweichungen und Entwicklungen zuverlässiger einordnen."
        )

    st.markdown("#### Empfehlung für dein nächstes Training")
    fallback = (
        "- **Einordnung:** Folge grundsätzlich deinem bestehenden Plan.\n"
        f'- **Optionale Ergänzung:** {weekly_focus.get("session", "Kein zusätzlicher Reiz erforderlich.")}\n'
        "- **Hinweis:** Die Ergänzung ersetzt weder das Programming noch eine geplante Haupteinheit."
    )
    with st.container(border=True):
        st.markdown(sections["next_session"] or fallback)

    st.markdown("#### Das läuft aktuell gut")
    positive_columns = st.columns(min(max(len(positive_observations[:3]), 1), 3))
    observations = positive_observations[:3] or [
        "Mit weiteren gespeicherten Einheiten werden belastbare positive Muster sichtbar."
    ]
    for index, observation in enumerate(observations):
        with positive_columns[index % len(positive_columns)]:
            with st.container(border=True):
                st.markdown(f"**{index + 1:02d}**")
                st.markdown(observation)

    st.markdown("#### Entwicklung auf einen Blick")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Training · 28 Tage", f"{int(sessions_28 or 0)} Einheiten")
    c2.metric(
        "Belastung · 14 Tage",
        load_trend.get("text", "Noch nicht bewertbar"),
        _metric_delta(load_trend.get("change_percent"), " %"),
    )
    c3.metric(
        "Routine · 28 Tage",
        consistency.get("text", "Noch nicht bewertbar"),
        f'{int(consistency.get("active_weeks", 0) or 0)} von 4 Wochen aktiv',
    )
    c4.metric(
        "Vielfalt · 28 Tage",
        diversity.get("text", "Noch nicht bewertbar"),
        (
            f'{float(diversity.get("score", 0) or 0):.0f} %'
            if diversity.get("score") is not None
            else None
        ),
    )

    with st.expander("Wie kommt die Empfehlung zustande?"):
        st.markdown(
            "Die App bewertet dein tatsächlich absolviertes Training, deine Belastungsverteilung "
            "und erkennbare Lücken. Sie ersetzt keinen Trainingsplan. Die Empfehlung zeigt nur, "
            "wie du dein bestehendes Programming sinnvoll einordnen, anpassen oder klein ergänzen kannst."
        )
