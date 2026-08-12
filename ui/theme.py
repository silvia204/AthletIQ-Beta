from __future__ import annotations

import streamlit as st


# ============================================================
# DESIGN TOKENS
# ============================================================
# Diese Werte sind die zentrale Stelle für Typografie, Abstände,
# Rundungen und Farben der gesamten App.

BASE_FONT_SIZE_PX = 14
CONTENT_MAX_WIDTH_PX = 1280


THEME_CSS = f"""
<style>
:root {{

    color-scheme: light;

    /* Typography */
    --app-font-size: 14px;

    /* Text */
    --text-primary: #0f172a;
    --text-secondary: #64748b;

    /* Surfaces */
    --surface-1: #ffffff;
    --surface-2: #f8fafc;
    --surface-3: #eef2f7;

    /* Borders */
    --border-color: rgba(148,163,184,.24);

    /* Status */
    --success-bg: rgba(240,253,244,.88);
    --warning-bg: rgba(255,251,235,.92);
    --danger-bg: rgba(254,242,242,.90);

    --success-border:#16a34a;
    --warning-border:#d97706;
    --danger-border:#dc2626;
    --accent-border:#64748b;

    /* Radius */
    --app-radius-sm:14px;
    --app-radius-md:16px;
    --app-radius-lg:18px;
    --app-radius-xl:20px;
}}

/* Dark Mode automatisch über Streamlit */

@media (prefers-color-scheme: dark){{

:root{{

    color-scheme: dark;

    --text-primary:#f8fafc;
    --text-secondary:#cbd5e1;

    --surface-1:#1f2937;
    --surface-2:#111827;
    --surface-3:#0f172a;

    --border-color:rgba(148,163,184,.30);
    --accent-border:#94a3b8;

    --success-bg:rgba(20,83,45,.45);
    --warning-bg:rgba(120,53,15,.45);
    --danger-bg:rgba(127,29,29,.45);

    --success-border: #22c55e;
    --warning-border: #f59e0b;
    --danger-border: #ef4444;

}}

}}

/* Globale Grundtypografie */
html {{
    font-size: var(--app-font-size) !important;
}}

body,
.stApp {{
    color: var(--text-primary);
    font-size: 1rem !important;
    background: var(--surface-2);
}}

/* Streamlit-Standardtexte übernehmen die zentrale Schriftgröße. */
.stApp p,
.stApp li,
.stApp label,
.stApp input,
.stApp textarea,
.stApp button,
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stCaptionContainer"] {{
    font-size: 1rem;
}}

/* Überschriften bewusst separat skalieren. */
.stApp h1 {{ font-size: 2rem; line-height: 1.2; }}
.stApp h2 {{ font-size: 1.6rem; line-height: 1.25; }}
.stApp h3 {{ font-size: 1.35rem; line-height: 1.3; }}
.stApp h4 {{ font-size: 1.15rem; line-height: 1.35; }}
.stApp h5 {{ font-size: 1.05rem; line-height: 1.35; }}

.block-container {{
    max-width: {CONTENT_MAX_WIDTH_PX}px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    font-size: 0.95rem !important;
}}

/* Kennzahlen */
div[data-testid="stMetric"] {{
    background: var(--surface-2);
    border: 1px solid var(--border-color);
    border-radius: var(--app-radius-md);
    padding: 0.9rem 1rem;
    min-height: 72px;
}}

/*
Streamlit setzt die Schriftgröße teilweise auf verschachtelte,
dynamisch erzeugte Elemente. Deshalb werden Container und alle
Elemente innerhalb des Metric-Wertes angesprochen.
*/
.stApp div[data-testid="stMetricValue"],
.stApp div[data-testid="stMetricValue"] *,
.stApp div[data-testid="stMetricValue"] div,
.stApp div[data-testid="stMetricValue"] p,
.stApp div[data-testid="stMetricValue"] span {{
    font-size: clamp(1.15rem, 1.5vw, 1.45rem) !important;
    line-height: 1.2 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: break-word !important;
}}

.stApp div[data-testid="stMetricLabel"],
.stApp div[data-testid="stMetricLabel"] *,
.stApp div[data-testid="stMetricLabel"] p {{
    font-size: 0.82rem !important;
    line-height: 1.3 !important;
}}

/* Karten */
.profile-card {{
    padding: 1rem 1.2rem;
    border: 1px solid var(--border-color);
    border-radius: var(--app-radius-lg);
    background: var(--surface-2);
    margin-bottom: 1rem;
}}

.coach-card {{
    padding: 1.1rem 1.25rem;
    border:1px solid var(--border-color);
    border-left:5px solid var(--accent-border);
    border-radius: var(--app-radius-md);
    background:var(--surface-2);
    line-height: 1.65;
    margin-bottom: 1rem;
}}

.finding-card {{
    padding: 0.9rem 1rem;
    border:1px solid var(--border-color);
    border-radius: var(--app-radius-sm);
    margin-bottom: 0.65rem;
    background: var(--surface-1);
}}

.muted-label {{
    color: var(--text-secondary);
    font-size: 0.82rem;
    margin-bottom: 0.2rem;
}}

.welcome-card {{
    padding: 1.2rem 1.35rem;
    border: 1px solid var(--border-color);
    border-radius: var(--app-radius-xl);
    background: linear-gradient(
        135deg,
        var(--surface-1),
        var(--surface-3)
    );
    margin-bottom: 1rem;
    font-size: 0.92rem;
}}

.welcome-title {{
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}}

.welcome-meta {{
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.4;
}}

.readiness-card {{
    padding: 1.1rem 1.2rem;
    border-radius: var(--app-radius-lg);
    border:1px solid var(--border-color);
    min-height: 152px;
    font-size: 0.95rem;
}}

.readiness-good {{
    background: var(--success-bg);
    border-left: 6px solid var(--success-border);
}}

.readiness-caution {{
    background: var(--warning-bg);
    border-left: 6px solid var(--warning-border);
}}

.readiness-recovery {{
    background: var(--danger-bg);
    border-left: 6px solid var(--danger-border);
}}

.readiness-title {{
    font-size: 1.05rem;
    font-weight: 700;
    margin: 0.15rem 0 0.45rem 0;
}}

.focus-card {{
    min-height: 150px;
    padding: 20px 22px;
    border: 1px solid rgba(120, 130, 145, 0.25);
    border-radius: 18px;
    box-sizing: border-box;
}}

.plan-card {{
    border-left: 5px solid #a0aec0;
}}

.supplement-card {{
    border-left: 5px solid #718096;
}}

.card-detail {{
    margin-top: 8px;
    line-height: 1.5;
}}

.card-note {{
    margin-top: 12px;
    font-size: 0.92rem;
}}

.positive-card {{
    padding: 0.82rem 0.95rem;
    border:1px solid var(--border-color);
    border-radius: var(--app-radius-sm);
    background:var(--surface-2);
    margin-bottom: 0.6rem;
    font-size: 0.95rem;
}}


.daily-tip-card {{
    width: 100%;
    min-height: 165px;
    padding: 20px 22px;
    border: 1px solid rgba(120, 130, 145, 0.25);
    border-radius: 18px;
    box-sizing: border-box;
    text-align: left;
}}

.daily-tip-label {{
    width: 100%;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    opacity: 0.58;
    margin-bottom: 8px;
}}

.daily-tip-title {{
    width: 100%;
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 10px;
}}

.daily-tip-text {{
    width: 100%;
    line-height: 1.5;
}}

</style>
"""


STATUS_DASHBOARD_CSS = r"""
<style>
.status-hero{padding:.3rem .1rem 1rem}.status-eyebrow{font-size:.78rem;font-weight:800;letter-spacing:.12em;color:#8b5cf6}.status-greeting{font-size:1.65rem;font-weight:760;margin-top:.25rem}.status-card{border:1px solid var(--border-color);border-radius:20px;background:var(--surface-1);padding:1.15rem 1.25rem;margin:.65rem 0 1rem;box-shadow:0 10px 30px rgba(0,0,0,.04)}.status-week-card{background:linear-gradient(135deg,var(--surface-1),var(--surface-3))}.status-card-heading,.status-section-title{font-size:.78rem;font-weight:800;letter-spacing:.06em}.status-section-title{margin:1.3rem 0 .45rem}.status-pill,.priority-pill{display:inline-block;border-radius:999px;padding:.28rem .65rem;font-size:.78rem;font-weight:700;margin:.65rem 0}.status-good{background:rgba(34,197,94,.14);color:#22c55e}.status-caution{background:rgba(245,158,11,.14);color:#f59e0b}.status-warn{background:rgba(239,68,68,.14);color:#ef4444}.status-metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem;margin-top:.35rem}.status-metric-grid>div{padding:.8rem;border:1px solid var(--border-color);border-radius:14px}.status-metric-grid strong{display:block;font-size:1.05rem}.status-metric-grid span{display:block;color:var(--text-secondary);font-size:.76rem;margin-top:.2rem}.status-finding{display:flex;gap:.65rem;align-items:flex-start;padding:.4rem 0}.finding-ok,.finding-note{display:inline-flex;align-items:center;justify-content:center;min-width:1.3rem;height:1.3rem;border-radius:50%;font-weight:800}.finding-ok{background:rgba(34,197,94,.16);color:#22c55e}.finding-note{background:rgba(245,158,11,.16);color:#f59e0b}.status-supplement-card{border-color:rgba(139,92,246,.65);background:linear-gradient(135deg,rgba(139,92,246,.08),var(--surface-1))}.supplement-row{display:flex;gap:1rem;justify-content:space-between;align-items:flex-start;margin-top:.6rem}.supplement-title,.latest-title{font-size:1.15rem;font-weight:750}.supplement-reason{color:var(--text-secondary);margin-top:.25rem;line-height:1.45}.priority-pill{background:rgba(139,92,246,.16);color:#8b5cf6;white-space:nowrap;margin:0}.status-latest-card{display:flex;align-items:center;justify-content:space-between}.latest-arrow{font-size:2rem;color:#8b5cf6}@media(max-width:700px){.status-metric-grid{grid-template-columns:repeat(2,1fr)}.supplement-row{flex-direction:column}.priority-pill{margin-top:.2rem}}
</style>
"""

def apply_theme() -> None:
    """Bindet das zentrale Design-System in die Streamlit-App ein."""
    st.markdown(THEME_CSS + STATUS_DASHBOARD_CSS, unsafe_allow_html=True)
# NOTE: additional CSS is injected separately below to keep the existing theme stable.
