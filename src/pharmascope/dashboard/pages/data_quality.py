"""Data quality visuals."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start


def render() -> None:
    hero(
        "Data Quality",
        "Severity-classified validation outcomes from pipeline promotion runs.",
    )
    reports = da.latest_dq_reports(30)
    if not reports:
        st.info("No data-quality reports yet. Run transformations to generate them.")
        return

    rows = []
    for rep in reports:
        for check in rep.get("checks", []):
            rows.append(
                {
                    "source": rep.get("source"),
                    "dataset": rep.get("dataset"),
                    "report_id": rep.get("report_id"),
                    "check_name": check.get("check_name"),
                    "severity": check.get("severity"),
                    "passed": check.get("passed"),
                    "failures": check.get("failures_detected"),
                    "failure_pct": check.get("failure_percentage"),
                    "action": check.get("recommended_action"),
                }
            )
    df = pd.DataFrame(rows)
    passed = int(df["passed"].sum()) if len(df) else 0
    failed = int((~df["passed"].astype(bool)).sum()) if len(df) else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("DQ reports", fmt_int(len(reports)))
    with c2:
        kpi("Checks passed", fmt_int(passed))
    with c3:
        kpi("Checks failed", fmt_int(failed))

    a, b = st.columns(2)
    with a:
        panel_start("Pass / fail mix")
        mix = pd.DataFrame(
            {"result": ["passed", "failed"], "count": [passed, failed]}
        )
        mix = mix[mix["count"] > 0]
        if not mix.empty:
            st.plotly_chart(
                charts.donut(mix, "result", "count", title="Check outcomes"),
                use_container_width=True,
            )
        panel_end()
    with b:
        panel_start("Failures by severity")
        sev = (
            df.loc[~df["passed"].astype(bool)]
            .groupby("severity", dropna=False)
            .size()
            .reset_index(name="count")
        )
        if not sev.empty:
            st.plotly_chart(
                charts.bar_rank(sev, "count", "severity", title="Failed checks"),
                use_container_width=True,
            )
        else:
            st.success("No failed checks in recent reports.")
        panel_end()

    panel_start("Check detail")
    st.dataframe(df, use_container_width=True, height=420)
    panel_end()
    st.json(reports[0])
