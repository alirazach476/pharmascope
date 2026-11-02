"""Statistical workbench with visual outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import hero, panel_end, panel_start
from pharmascope.statistics.confidence_intervals import proportion_ci_wilson
from pharmascope.statistics.hypothesis_tests import chi_square_independence
from pharmascope.statistics.safety_signals import ContingencyTable, reporting_odds_ratio
from pharmascope.statistics.sensitivity_analysis import ror_continuity_sensitivity
from pharmascope.statistics.time_series import rolling_origin_backtest


def render() -> None:
    hero(
        "Statistical Workbench",
        "Validated analysis functions only — no arbitrary SQL. Results include methods, "
        "sample sizes, and limitations.",
    )
    tables = da.list_tables()
    analysis = st.selectbox(
        "Analysis",
        [
            "Serious report proportion (Wilson CI)",
            "Recall classification chi-square",
            "Exploratory ROR + sensitivity",
            "AE monthly volume naive backtest",
        ],
    )

    if analysis == "Serious report proportion (Wilson CI)":
        if "fact_adverse_event_reports" not in tables:
            st.warning("fact_adverse_event_reports not loaded.")
            return
        df = da.query(
            """
            SELECT serious FROM fact_adverse_event_reports
            WHERE COALESCE(synthetic, FALSE) = FALSE
            """
        )
        serious = df["serious"].astype(str).isin(["1", "1.0"])
        n = len(df)
        successes = int(serious.sum())
        est = proportion_ci_wilson(successes, n)
        panel_start("Wilson score interval")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("n", n)
        m2.metric("Serious reports", successes)
        m3.metric("Proportion", f"{est.estimate:.3f}")
        m4.metric("95% CI", f"[{est.lower:.3f}, {est.upper:.3f}]")
        viz = pd.DataFrame(
            {
                "label": ["Lower CI", "Estimate", "Upper CI"],
                "value": [est.lower, est.estimate, est.upper],
            }
        )
        st.plotly_chart(
            charts.bar_rank(viz, "value", "label", title="Proportion and Wilson bounds", orientation="h"),
            use_container_width=True,
        )
        st.caption("Sample of OpenFDA extracts — not incidence in a population.")
        panel_end()

    elif analysis == "Recall classification chi-square":
        if "fact_recalls" not in tables:
            st.warning("fact_recalls not loaded.")
            return
        df = da.query(
            """
            SELECT classification,
                   CASE WHEN status = 'Terminated' THEN 'Terminated' ELSE 'Other' END AS status_group
            FROM fact_recalls
            WHERE classification IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
            """
        )
        crosstab = pd.crosstab(df["classification"], df["status_group"])
        panel_start("Contingency + chi-square")
        st.dataframe(crosstab, use_container_width=True)
        result = chi_square_independence(crosstab.to_numpy())
        st.plotly_chart(charts.heatmap(crosstab, title="Classification × status"), use_container_width=True)
        st.json(
            {
                "test": result.test_name,
                "statistic": result.statistic,
                "pvalue": result.pvalue,
                "effect_size": result.effect_size,
                "effect_size_name": result.effect_size_name,
                "warnings": result.warnings,
            }
        )
        panel_end()

    elif analysis == "Exploratory ROR + sensitivity":
        a = st.number_input("a (drug+event)", min_value=0, value=10)
        b = st.number_input("b (drug only)", min_value=0, value=20)
        c = st.number_input("c (event only)", min_value=0, value=30)
        d = st.number_input("d (neither)", min_value=0, value=100)
        table = ContingencyTable(a=int(a), b=int(b), c=int(c), d=int(d))
        base = reporting_odds_ratio(table, drug="user", event="user")
        sens = ror_continuity_sensitivity(table)
        panel_start("ROR sensitivity across continuity corrections")
        sens_df = pd.DataFrame([s.__dict__ for s in sens])
        st.dataframe(sens_df, use_container_width=True)
        plot_df = sens_df.dropna(subset=["ror"])
        if not plot_df.empty:
            st.plotly_chart(
                charts.line_trend(
                    plot_df.assign(correction=plot_df["continuity_correction"].astype(str)),
                    "correction",
                    "ror",
                    title="ROR vs continuity correction",
                ),
                use_container_width=True,
            )
        st.json({"label": base.label, "ror": base.ror, "notes": base.notes})
        panel_end()

    elif analysis == "AE monthly volume naive backtest":
        if "fact_adverse_event_reports" not in tables:
            st.warning("fact_adverse_event_reports not loaded.")
            return
        trends = da.query(
            """
            SELECT strftime(CAST(receivedate AS DATE), '%Y-%m') AS year_month,
                   COUNT(DISTINCT safetyreportid) AS report_count
            FROM fact_adverse_event_reports
            WHERE receivedate IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY 1
            """
        )
        if len(trends) < 8:
            st.warning("Need at least 8 monthly points for a minimal backtest.")
            st.dataframe(trends)
            return
        bt = rolling_origin_backtest(
            trends["report_count"].tolist(), horizon=1, min_train=3, method="naive"
        )
        panel_start("Chronological naive backtest")
        m1, m2, m3 = st.columns(3)
        m1.metric("MAE", f"{bt.metrics.mae:.3f}")
        m2.metric("RMSE", f"{bt.metrics.rmse:.3f}")
        m3.metric("Points", bt.metrics.n)
        cmp = pd.DataFrame({"actual": bt.actuals, "predicted": bt.predictions})
        cmp["index"] = np.arange(len(cmp))
        long = cmp.melt(id_vars=["index"], value_vars=["actual", "predicted"], var_name="series", value_name="value")
        st.plotly_chart(
            charts.line_trend(long, "index", "value", color="series", title="Backtest actual vs predicted"),
            use_container_width=True,
        )
        st.caption("FAERS volumes are not medicine demand; reporting practice changes matter.")
        panel_end()
