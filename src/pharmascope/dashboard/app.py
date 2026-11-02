"""PharmaScope Streamlit dashboard — rich analytics UI.

Launch::

    streamlit run src/pharmascope/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from pharmascope import __disclaimer__, __version__
from pharmascope.dashboard.pages import (
    data_quality,
    market_analytics,
    medicine_explorer,
    overview,
    pipeline_monitor,
    recall_analytics,
    safety_analytics,
    statistical_analysis,
)
from pharmascope.dashboard.theme import apply_theme

st.set_page_config(
    page_title="PharmaScope Intelligence",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

PAGES = {
    "Executive Overview": overview.render,
    "Medicine Explorer": medicine_explorer.render,
    "Drug Safety Analytics": safety_analytics.render,
    "Recall Intelligence": recall_analytics.render,
    "Market & Products": market_analytics.render,
    "Statistical Workbench": statistical_analysis.render,
    "Data Quality": data_quality.render,
    "Pipeline Monitor": pipeline_monitor.render,
}


def main() -> None:
    with st.sidebar:
        st.markdown("## PharmaScope")
        st.caption(f"Intelligence platform · v{__version__}")
        st.markdown("---")
        page = st.radio("Workspace", list(PAGES.keys()), label_visibility="collapsed")
        st.markdown("---")
        st.caption(__disclaimer__)
    PAGES[page]()


if __name__ == "__main__":
    main()
