"""Pipeline monitor with timeline visuals."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start
from pharmascope.monitoring.freshness import freshness_ages_hours


def render() -> None:
    hero(
        "Pipeline Monitor",
        "Historical extraction metrics from manifests — not live ops telemetry.",
    )
    manifests = da.latest_manifests(80)
    if not manifests:
        st.info("No manifests found under data/metadata/manifests.")
        return

    df = pd.DataFrame(
        [
            {
                "source": m.get("source_name"),
                "status": m.get("status"),
                "mode": m.get("extraction_mode"),
                "records": m.get("raw_record_count") or 0,
                "pages": m.get("page_count") or 0,
                "started_at": m.get("started_at"),
                "finished_at": m.get("finished_at"),
                "error": m.get("error_details"),
                "manifest_id": m.get("manifest_id"),
            }
            for m in manifests
        ]
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Manifests", fmt_int(len(df)))
    with c2:
        kpi("Success", fmt_int(int((df["status"] == "success").sum())))
    with c3:
        kpi("Failed", fmt_int(int((df["status"] == "failed").sum())))
    with c4:
        kpi("Records pulled", fmt_int(int(df["records"].sum())))

    a, b = st.columns(2)
    with a:
        panel_start("Records by source")
        by_source = df.groupby("source", as_index=False)["records"].sum()
        st.plotly_chart(
            charts.bar_rank(by_source, "records", "source", title="Extracted records"),
            use_container_width=True,
        )
        panel_end()
    with b:
        panel_start("Status distribution")
        by_status = df.groupby("status", as_index=False).size().rename(columns={"size": "count"})
        st.plotly_chart(
            charts.donut(by_status, "status", "count", title="Run status"),
            use_container_width=True,
        )
        panel_end()

    ages = freshness_ages_hours()
    if ages:
        panel_start("Data freshness (hours since last success)")
        age_df = pd.DataFrame(
            [{"source": k, "hours": v} for k, v in ages.items() if v is not None]
        )
        if not age_df.empty:
            st.plotly_chart(
                charts.bar_rank(age_df, "hours", "source", title="Freshness lag"),
                use_container_width=True,
            )
        panel_end()

    panel_start("Run history")
    st.dataframe(df, use_container_width=True, height=360)
    panel_end()
    idx = st.number_input("Inspect row index", min_value=0, max_value=max(len(manifests) - 1, 0), value=0)
    st.json(manifests[int(idx)])
