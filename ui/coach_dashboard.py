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
    daily_coach_tips: dict[str, str],
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

    st.markdown("### Analyse · Ergänzen · Entwicklung")
    st.caption(
        "Dein Coach bewertet dein absolviertes Training, erkennt Muster und zeigt sinnvolle Ergänzungen – ohne dir einen Trainingsplan vorzugeben."
    )

    # ----------------------------------------------------
    # AKTUELLE BELASTBARKEIT
    # ----------------------------------------------------

    readiness_detail = (
        readiness.get("detail")
        or (
            "Aktuell gibt es keine Hinweise, die eine Anpassung "
            "deines geplanten Trainings erforderlich machen."
        )
    )

    st.markdown(
        (
            f'<div class="readiness-card '
            f'{_safe(readiness.get("css_class"), "readiness-good")}">'
            '<div class="muted-label">'
            'AKTUELLE BELASTBARKEIT'
            '</div>'
            '<div class="readiness-title">'
            f'{_safe(readiness.get("icon"), "🟢")} '
            f'{_safe(readiness.get("label"), "Trainingsstatus")}'
            '</div>'
            '<div class="readiness-detail">'
            f'{_safe(readiness_detail)}'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.markdown("#### Das läuft gut")
    if positive_observations:
        cols = st.columns(min(3, len(positive_observations)), gap="medium")
        for index, observation in enumerate(positive_observations[:6]):
            if isinstance(observation, dict):
                title = observation.get("title", "Positive Entwicklung")
                message = observation.get("message", observation.get("text", ""))
            else:
                title, message = "Positive Entwicklung", str(observation)
            with cols[index % len(cols)]:
                st.markdown(
                    f'<div class="positive-card"><strong>✓ {_safe(title)}</strong><div>{_safe(message)}</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("Noch nicht genügend Daten für belastbare positive Trends.")

    # ----------------------------------------------------
    # SINNVOLLE ERGÄNZUNG
    # ----------------------------------------------------

    st.markdown(
        "#### Sinnvoll ergänzen"
    )

    guidance_left, guidance_right = st.columns(
        2,
        gap="medium",
    )

    with guidance_left:

        plan_guidance = (
            readiness.get("plan_guidance")
            or "Folge grundsätzlich deinem bestehenden Trainingsplan."
        )

        avoid = readiness.get("avoid")

        plan_content = (
            '<div class="focus-card plan-card">'
            '<div class="muted-label">'
            'EINORDNUNG ZUM PLAN'
            '</div>'
            '<div class="readiness-title">'
            'Bestehenden Plan beibehalten'
            '</div>'
            '<div class="card-detail">'
            f'{_safe(plan_guidance)}'
            '</div>'
        )

        if avoid:
            plan_content += (
                '<div class="card-note">'
                '<strong>Aktuell vermeiden:</strong> '
                f'{_safe(avoid)}'
                '</div>'
            )

        plan_content += "</div>"

        st.markdown(
            plan_content,
            unsafe_allow_html=True,
        )


    with guidance_right:

        focus_title = _safe(
            weekly_focus.get("title"),
            "Aktueller Fokus",
        )

        focus_text = (
            weekly_focus.get("text")
            or (
                "Wenn es zu deiner geplanten Einheit passt, "
                "berücksichtige aktuell wenig trainierte Bereiche."
            )
        )

        st.markdown(
            (
                '<div class="focus-card supplement-card">'
                '<div class="muted-label">'
                'SINNVOLLE ERGÄNZUNG'
                '</div>'
                '<div class="readiness-title">'
                f'{focus_title}'
                '</div>'
                '<div class="card-detail">'
                f'{_safe(focus_text)}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    # ----------------------------------------------------
    # ERGÄNZUNGEN UND RECOVERY
    # ----------------------------------------------------

    st.markdown("#### Ergänzende Hinweise")

    training_tip = _safe(
        daily_coach_tips.get("training"),
        "Folge deinem bestehenden Trainingsplan.",
    )

    nutrition_tip = _safe(
        daily_coach_tips.get("nutrition"),
        "Versorge dich passend zu deiner Trainingsbelastung.",
    )

    recovery_tip = _safe(
        daily_coach_tips.get("recovery"),
        "Plane Erholung passend zu deiner aktuellen Belastung ein.",
    )

    tip_training, tip_nutrition, tip_recovery = (
        st.columns(
            3,
            gap="medium",
        )
    )

    with tip_training:
        st.markdown(
            (
                '<div class="daily-tip-card">'
                '<div class="muted-label">TRAINING</div>'
                '<div class="daily-tip-title">'
                'Gezielter Zusatzreiz'
                '</div>'
                '<div class="daily-tip-text">'
                f'{training_tip}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with tip_nutrition:
        st.markdown(
            (
                '<div class="daily-tip-card">'
                '<div class="muted-label">ERNÄHRUNG</div>'
                '<div class="daily-tip-title">'
                'Fuel für heute'
                '</div>'
                '<div class="daily-tip-text">'
                f'{nutrition_tip}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    with tip_recovery:
        st.markdown(
            (
                '<div class="daily-tip-card">'
                '<div class="muted-label">RECOVERY</div>'
                '<div class="daily-tip-title">'
                'Erholung im Blick'
                '</div>'
                '<div class="daily-tip-text">'
                f'{recovery_tip}'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )


    st.markdown("### Deine Entwicklung")
    st.caption("28-Tage-Bild und aktuelle Veränderung deiner Belastung, Routine und Trainingsvielfalt.")
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
