"""Dashboard visual theme — applied once per Streamlit session."""

from __future__ import annotations

import streamlit as st

# Professional clinical analytics palette (avoid purple/indigo AI clichés)
COLORS = {
    "bg": "#0b1220",
    "panel": "#121a2b",
    "panel_alt": "#182338",
    "border": "#243049",
    "text": "#e8eef8",
    "muted": "#93a0b8",
    "accent": "#1aa6a0",
    "accent_2": "#3d8bfd",
    "warn": "#e6a23c",
    "danger": "#e35d6a",
    "ok": "#3dbf8a",
    "series": ["#1aa6a0", "#3d8bfd", "#e6a23c", "#8b7cf6", "#e35d6a", "#5ad1e6", "#f0c14a"],
}

PLOTLY_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": COLORS["text"], "family": "IBM Plex Sans, Segoe UI, sans-serif"},
    "margin": {"l": 48, "r": 24, "t": 48, "b": 48},
    "legend": {"bgcolor": "rgba(0,0,0,0)", "orientation": "h", "y": 1.08},
    "xaxis": {
        "gridcolor": COLORS["border"],
        "zerolinecolor": COLORS["border"],
        "linecolor": COLORS["border"],
    },
    "yaxis": {
        "gridcolor": COLORS["border"],
        "zerolinecolor": COLORS["border"],
        "linecolor": COLORS["border"],
    },
    "colorway": COLORS["series"],
}


def apply_theme() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"]  {{
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}}

.stApp {{
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(26,166,160,0.18), transparent 55%),
    radial-gradient(900px 500px at 90% 0%, rgba(61,139,253,0.14), transparent 50%),
    linear-gradient(180deg, #070b14 0%, {COLORS["bg"]} 40%, #0a101c 100%);
  color: {COLORS["text"]};
}}

[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #0d1524 0%, #0a1220 100%);
  border-right: 1px solid {COLORS["border"]};
}}

[data-testid="stSidebar"] * {{
  color: {COLORS["text"]} !important;
}}

.ps-hero {{
  padding: 1.25rem 1.5rem;
  border: 1px solid {COLORS["border"]};
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(26,166,160,0.16), rgba(61,139,253,0.08) 45%, rgba(18,26,43,0.9));
  box-shadow: 0 20px 50px rgba(0,0,0,0.35);
  margin-bottom: 1.25rem;
}}
.ps-hero h1 {{
  margin: 0;
  font-size: 2.1rem;
  letter-spacing: -0.03em;
  font-weight: 700;
}}
.ps-hero p {{
  margin: 0.45rem 0 0 0;
  color: {COLORS["muted"]};
  max-width: 70ch;
  line-height: 1.45;
}}
.ps-badge {{
  display: inline-block;
  margin-top: 0.75rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  border: 1px solid rgba(26,166,160,0.45);
  color: {COLORS["accent"]};
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}

.ps-kpi {{
  border: 1px solid {COLORS["border"]};
  border-radius: 16px;
  padding: 1rem 1.1rem;
  background: linear-gradient(180deg, {COLORS["panel_alt"]}, {COLORS["panel"]});
  min-height: 118px;
}}
.ps-kpi .label {{
  color: {COLORS["muted"]};
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}}
.ps-kpi .value {{
  font-size: 1.85rem;
  font-weight: 700;
  margin-top: 0.35rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}}
.ps-kpi .hint {{
  margin-top: 0.35rem;
  color: {COLORS["muted"]};
  font-size: 0.78rem;
}}

.ps-panel {{
  border: 1px solid {COLORS["border"]};
  border-radius: 16px;
  padding: 1rem 1.1rem 0.4rem 1.1rem;
  background: rgba(18,26,43,0.88);
  margin-bottom: 1rem;
}}
.ps-panel h3 {{
  margin: 0 0 0.35rem 0;
  font-size: 1.05rem;
}}
.ps-panel .sub {{
  color: {COLORS["muted"]};
  font-size: 0.82rem;
  margin-bottom: 0.6rem;
}}

div[data-testid="stMetric"] {{
  background: {COLORS["panel"]};
  border: 1px solid {COLORS["border"]};
  border-radius: 14px;
  padding: 0.75rem 0.9rem;
}}

.stDataFrame, [data-testid="stDataFrame"] {{
  border: 1px solid {COLORS["border"]};
  border-radius: 12px;
  overflow: hidden;
}}

.stAlert {{
  border-radius: 12px;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, badge: str = "Authentic public data") -> None:
    st.markdown(
        f"""
<div class="ps-hero">
  <div class="ps-badge">{badge}</div>
  <h1>{title}</h1>
  <p>{subtitle}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, hint: str = "") -> None:
    st.markdown(
        f"""
<div class="ps-kpi">
  <div class="label">{label}</div>
  <div class="value">{value}</div>
  <div class="hint">{hint}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def panel_start(title: str, subtitle: str = "") -> None:
    sub = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="ps-panel"><h3>{title}</h3>{sub}',
        unsafe_allow_html=True,
    )


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def fmt_int(n: int | float | None) -> str:
    if n is None:
        return "—"
    return f"{int(n):,}"
