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
    first_name = (user_name or "Athlet").strip().split()[0]
    label, css_class = _status_label(readiness)

    active_weeks = int(consistency.get("active_weeks", 0) or 0)
    diversity_text = diversity.get("text", "Noch nicht bewertbar")
    load_text = load_trend.get("text", "Noch nicht bewertbar")

    st.markdown(
        f'''<div class="status-card status-week-card">
        <div class="status-card-heading">DEINE WOCHE</div>
        <span class="status-pill {css_class}">{_safe(label)}</span>
        <div class="status-metric-grid">
          <div><strong>{int(sessions_28 or 0)}</strong><span>Einheiten · 28 Tage</span></div>
          <div><strong>{_safe(load_text)}</strong><span>Belastung</span></div>
          <div><strong>{active_weeks}/4</strong><span>aktive Wochen</span></div>
          <div><strong>{_safe(diversity_text)}</strong><span>Vielfalt</span></div>
        </div></div>''',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="status-section-title">DAS FÄLLT DEINEM COACH AUF</div>', unsafe_allow_html=True)
    observations: list[str] = []
    for item in positive_observations or []:
        if isinstance(item, dict):
            observations.append(str(item.get("message") or item.get("title") or "").strip())
        else:
            observations.append(str(item).strip())
    observations = [x for x in observations if x][:2]
    if not observations:
        observations = ["Deine Trainingshistorie wird mit jeder gespeicherten Einheit aussagekräftiger."]

    finding_html = "".join(
        f'<div class="status-finding"><span class="finding-ok">✓</span><span>{_safe(text)}</span></div>'
        for text in observations
    )
    focus_reason = str(weekly_focus.get("reason") or "").strip()
    if focus_reason:
        finding_html += f'<div class="status-finding"><span class="finding-note">!</span><span>{_safe(focus_reason)}</span></div>'
    st.markdown(f'<div class="status-card">{finding_html}</div>', unsafe_allow_html=True)

    focus_title = weekly_focus.get("title") or "Aktuell keine gezielte Ergänzung nötig"
    priority = str(weekly_focus.get("priority") or "low").lower()
    priority_label = {"high": "Hohe Priorität", "medium": "Mittlere Priorität", "low": "Optional"}.get(priority, "Optional")
    st.markdown(
        f'''<div class="status-card status-supplement-card">
        <div class="status-card-heading">SINNVOLLE ERGÄNZUNG</div>
        <div class="supplement-row"><div><div class="supplement-title">{_safe(focus_title)}</div>
        <div class="supplement-reason">{_safe(focus_reason, "Dein aktuelles Training zeigt keine dringende Lücke.")}</div></div>
        <span class="priority-pill">{_safe(priority_label)}</span></div></div>''',
        unsafe_allow_html=True,
    )
    st.button("Ergänzungen ansehen", key="status_show_supplements", width="stretch")

    st.markdown(
        f'''<div class="status-card status-latest-card"><div>
        <div class="status-card-heading">LETZTE EINHEIT</div>
        <div class="latest-title">{_safe(latest_workout_name)}</div>
        <div class="supplement-reason">{_safe(latest_workout_meta)}</div></div>
        <div class="latest-arrow">›</div></div>''',
        unsafe_allow_html=True,
    )
    st.button("Coach-Analyse ansehen", key="status_show_latest_analysis", width="stretch")

    st.markdown('<div class="status-section-title">DEINE ENTWICKLUNG · LETZTE 28 TAGE</div>', unsafe_allow_html=True)
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
        st.caption("Letzte 14 Tage im Vergleich zu den vorherigen 14 Tagen")
        trend_lines = []
        if frequency_data.get("text"):
            trend_lines.append(str(frequency_data["text"]))
        if rpe_data.get("text"):
            trend_lines.append(str(rpe_data["text"]))
        for item in (trend_analysis.get("movement_patterns", []) or [])[:2]:
            text = str(item.get("text") or "").strip()
            symbol = str(item.get("symbol") or "•")
            if text:
                trend_lines.append(f"{symbol} {text}")
        if trend_lines:
            st.markdown("  ".join(f"- {line}" for line in trend_lines))
    else:
        st.caption("Sobald Trainings gespeichert sind, erscheinen hier belastbare 28-Tage-Trends.")
