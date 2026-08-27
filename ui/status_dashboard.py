from __future__ import annotations

import html
from typing import Any

import streamlit as st


def _safe(value: object, fallback: str = "") -> str:
    return html.escape(str(value if value not in (None, "") else fallback))


def _status_label(readiness: dict[str, Any]) -> tuple[str, str]:
    status = str(readiness.get("status", "high")).lower()
    if status == "low":
        return "Belastung im Blick behalten", "status-warn"
    if status in {"medium", "caution"}:
        return "Etwas unausgewogen", "status-caution"
    return "Gut ausbalanciert", "status-good"


def _is_meaningful_focus(weekly_focus: dict[str, Any]) -> bool:
    title = str(weekly_focus.get("title") or "").strip().casefold()
    text = str(
        weekly_focus.get("text")
        or weekly_focus.get("reason")
        or ""
    ).strip()
    mode = str(weekly_focus.get("mode") or "").strip().casefold()

    generic_titles = {
        "",
        "training fortsetzen",
        "bestehenden plan beibehalten",
        "plan beibehalten",
        "unterrepräsentierte bereiche trainieren",
        "bestehenden rhythmus unterstützen",
        "programming ausgewogen umsetzen",
        "programming zielgerichtet ergänzen",
        "laufplan unterstützen",
    }

    meaningful_modes = {
        "missing_component",
        "load_adjustment",
        "small_add_on",
        "crossfit",
    }

    return bool(
        text
        and title not in generic_titles
        and mode in meaningful_modes
    )


def render_status_dashboard(
    *,
    user_name: str,
    sessions_28: int,
    readiness: dict[str, Any],
    positive_observations: list[Any],
    weekly_focus: dict[str, Any],
    load_trend: dict[str, Any],
    consistency: dict[str, Any],
    diversity: dict[str, Any],
    latest_workout_name: str = "Letzte erfasste Einheit",
    latest_workout_meta: str = "Coach-Einordnung verfügbar",
    trend_analysis: dict[str, Any] | None = None,
    recent_sessions: list[dict[str, Any]] | None = None,
) -> None:
    label, css_class = _status_label(readiness)
    active_weeks = int(consistency.get("active_weeks", 0) or 0)
    diversity_text = diversity.get("text", "Noch nicht bewertbar")
    load_text = load_trend.get("text", "Noch nicht bewertbar")

    st.markdown(
        f'''<div class="status-card status-week-card">
        <div class="status-card-heading">ÜBERSICHT · LETZTE 28 TAGE</div>
        <span class="status-pill {css_class}">{_safe(label)}</span>
        <div class="status-metric-grid">
          <div><strong>{int(sessions_28 or 0)}</strong><span>Einheiten</span></div>
          <div><strong>{_safe(load_text)}</strong><span>Belastung</span></div>
          <div><strong>{active_weeks}/4</strong><span>aktive Wochen</span></div>
          <div><strong>{_safe(diversity_text)}</strong><span>Vielfalt</span></div>
        </div></div>''',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="status-section-title">DAS FÄLLT DEINEM COACH AUF</div>',
        unsafe_allow_html=True,
    )
    observations: list[str] = []
    for item in positive_observations or []:
        if isinstance(item, dict):
            text = str(item.get("message") or item.get("title") or "").strip()
        else:
            text = str(item).strip()
        if text and text not in observations:
            observations.append(text)

    observations = observations[:2]

    focus_title = str(weekly_focus.get("title") or "").strip()

    focus_reason = str(
        weekly_focus.get("text")
        or weekly_focus.get("reason")
        or ""
    ).strip()

    focus_mode = str(
        weekly_focus.get("mode")
        or ""
    ).strip().casefold()

    focus_session = str(weekly_focus.get("session") or "").strip()
    focus_recommendation_reason = str(
        weekly_focus.get("recommendation_reason") or ""
    ).strip()

    meaningful_focus = _is_meaningful_focus(weekly_focus)

    finding_rows = [
        f'<div class="status-finding"><span class="finding-ok">✓</span><span>{_safe(text)}</span></div>'
        for text in observations
    ]

    # Die priorisierte Lücke wird bereits als Coach-Beobachtung sichtbar.
    # Dadurch folgt die Übersicht der Logik: Daten -> Beobachtung -> Konsequenz.
    if meaningful_focus and focus_reason:
        finding_rows.append(
            f'<div class="status-finding"><span class="finding-note">!</span><span>{_safe(focus_reason)}</span></div>'
        )

    if not finding_rows:
        finding_rows.append(
            '<div class="status-finding"><span class="finding-ok">✓</span>'
            '<span>Mit weiteren gespeicherten Einheiten werden die Coach-Beobachtungen belastbarer.</span></div>'
        )

    st.markdown(
        f'<div class="status-card">{"".join(finding_rows[:3])}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="status-section-title">DESHALB SINNVOLL</div>',
        unsafe_allow_html=True,
    )
    if meaningful_focus:
        mode_label = {
            "missing_component": "Mögliche Ergänzung",
            "load_adjustment": "Belastung anpassen",
            "small_add_on": "Optionale Ergänzung",
            "crossfit": "CrossFit-Ergänzung",
        }.get(
            focus_mode,
            "Mögliche Ergänzung",
        )

        recommendation_html = (
            '<div class="supplement-session"><strong>Konkreter Vorschlag:</strong> '
            + _safe(focus_session)
            + '</div>'
            if focus_session
            else ""
        )
        explanation = focus_recommendation_reason or focus_reason

        card_html = (
            '<div class="status-card status-supplement-card">'
            '<div class="supplement-row"><div>'
            '<div class="supplement-title">' + _safe(focus_title) + '</div>'
            + recommendation_html
            + '<div class="supplement-reason">' + _safe(explanation) + '</div></div>'
            '<span class="priority-pill">' + _safe(mode_label) + '</span></div></div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        with st.expander("Warum ist das sinnvoll?", expanded=False):
            detail_by_mode = {
                "crossfit": (
                    "Die Movement-Coverage wird mit deinen dokumentierten Trainingszielen "
                    "abgeglichen. Eine fehlende Bewegung wird deshalb nicht automatisch zu "
                    "einer Pflicht-Einheit: Entscheidend ist, ob die übrigen Daten zusätzlich "
                    "einen passenden Trainingsreiz als unterrepräsentiert zeigen."
                ),
                "missing_component": (
                    "Die Empfehlung priorisiert einen Trainingsbestandteil, der in deiner "
                    "bisherigen Verteilung vergleichsweise wenig vertreten ist. Sie ist als "
                    "gezielte Ergänzung gedacht, nicht als Ersatz für dein Programming."
                ),
                "load_adjustment": (
                    "Hier steht nicht ein zusätzliches Training im Vordergrund, sondern die "
                    "Einordnung deiner bisherigen Belastung. Die Empfehlung soll helfen, den "
                    "nächsten Reiz passend zur dokumentierten Belastungsverteilung zu wählen."
                ),
                "small_add_on": (
                    "Aus den bisherigen Daten ergibt sich keine große Trainingslücke. Deshalb "
                    "bleibt der Vorschlag bewusst klein und lässt sich nur dann ergänzen, wenn "
                    "dein bestehendes Programming dafür Spielraum lässt."
                ),
            }
            st.write(
                detail_by_mode.get(
                    focus_mode,
                    "Der Vorschlag leitet sich aus deiner bisherigen Trainingsverteilung ab "
                    "und ordnet eine mögliche Ergänzung in dein bestehendes Programming ein.",
                )
            )
            st.caption(
                "Die Empfehlung ergänzt deinen bestehenden Plan und ersetzt keine vollständige Trainingsplanung."
            )

    else:
        st.markdown(
            '''<div class="status-card status-supplement-card">
            <div class="supplement-title">Aktuell keine klare Trainingslücke</div>
            <div class="supplement-reason">
            Aus den bisherigen Daten ergibt sich derzeit keine einzelne Ergänzung,
            die gegenüber deinem bestehenden Training klar priorisiert werden sollte.
            </div>
            </div>''',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'''<div class="status-card status-latest-card"><div>
        <div class="status-card-heading">LETZTE EINHEIT</div>
        <div class="latest-title">{_safe(latest_workout_name)}</div>
        <div class="supplement-reason">{_safe(latest_workout_meta)}</div></div>
        <div class="latest-arrow">›</div></div>''',
        unsafe_allow_html=True,
    )
    st.caption("Die vollständigen Workout-Details findest du unter „Training“.")

    st.markdown(
        '<div class="status-section-title">DEINE ENTWICKLUNG · 28 TAGE</div>',
        unsafe_allow_html=True,
    )
    trend_analysis = trend_analysis or {}
    recent_sessions = recent_sessions or []
    load_data = trend_analysis.get("load", {}) or {}
    frequency_data = trend_analysis.get("frequency", {}) or {}
    rpe_data = trend_analysis.get("rpe", {}) or {}

    c1, c2, c3 = st.columns(3)
    c1.metric("Konsistenz", f"{active_weeks}/4 Wochen")
    c2.metric(
        "Belastung",
        str(load_text),
        delta=(
            f"{load_data.get('change_percent'):+.0f} %"
            if load_data.get("change_percent") is not None
            else None
        ),
    )
    c3.metric("Vielfalt", str(diversity_text))

    if recent_sessions:
        trend_lines: list[str] = []
        if frequency_data.get("text"):
            trend_lines.append(str(frequency_data["text"]))
        if rpe_data.get("text"):
            trend_lines.append(str(rpe_data["text"]))
        if trend_lines:
            st.caption(" · ".join(trend_lines[:2]))
    else:
        st.caption(
            "Sobald Trainings gespeichert sind, erscheinen hier belastbare 28-Tage-Trends."
        )
