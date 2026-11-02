"""Drug safety analytics with rich visualizations — reported cases only."""

from __future__ import annotations

import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start
from pharmascope.statistics.safety_signals import (
    build_drug_event_contingency,
    reporting_odds_ratio,
)


def render() -> None:
    hero(
        "Drug Safety Analytics",
        "Exploratory reporting patterns from FAERS via OpenFDA. High report counts do "
        "not mean a medicine is dangerous. ROR is not relative risk or proof of causation.",
        badge="Reported cases · not causal findings",
    )
    tables = da.list_tables()
    if "fact_adverse_event_reports" not in tables:
        st.info("Load openfda_events gold tables to use this page.")
        return

    kpis = da.warehouse_kpis()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Reports", fmt_int(kpis["reports"]))
    with c2:
        kpi("Drug rows", fmt_int(kpis["reported_drugs"]))
    with c3:
        kpi("Reaction rows", fmt_int(kpis["reactions"]))
    with c4:
        kpi("Pairs", fmt_int(kpis["drug_event_pairs"]))

    top_drugs = da.query(
        """
        SELECT medicinalproduct AS product,
               COUNT(DISTINCT safetyreportid) AS reports
        FROM dim_reported_drugs
        WHERE medicinalproduct IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1 ORDER BY reports DESC LIMIT 20
        """
    )
    top_rxn = da.query(
        """
        SELECT reaction_pt AS reaction,
               COUNT(DISTINCT safetyreportid) AS reports
        FROM dim_reported_reactions
        WHERE reaction_pt IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1 ORDER BY reports DESC LIMIT 20
        """
    )
    trends = da.query(
        """
        SELECT strftime(CAST(receivedate AS DATE), '%Y-%m') AS year_month,
               COUNT(DISTINCT safetyreportid) AS report_count,
               SUM(CASE WHEN CAST(serious AS VARCHAR) IN ('1','1.0') THEN 1 ELSE 0 END) AS serious_rows
        FROM fact_adverse_event_reports
        WHERE receivedate IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1 ORDER BY 1
        """
    )
    outcomes = da.query(
        """
        SELECT
          SUM(CASE WHEN CAST(seriousnessdeath AS VARCHAR) IN ('1','1.0') THEN 1 ELSE 0 END) AS death_flag,
          SUM(CASE WHEN CAST(seriousnesshospitalization AS VARCHAR) IN ('1','1.0') THEN 1 ELSE 0 END) AS hosp_flag,
          SUM(CASE WHEN CAST(seriousnesslifethreatening AS VARCHAR) IN ('1','1.0') THEN 1 ELSE 0 END) AS life_flag,
          SUM(CASE WHEN CAST(seriousnessdisabling AS VARCHAR) IN ('1','1.0') THEN 1 ELSE 0 END) AS disable_flag,
          COUNT(*) AS reports
        FROM fact_adverse_event_reports
        WHERE COALESCE(synthetic, FALSE) = FALSE
        """
    )

    panel_start("Reporting volume & seriousness", "Distinct reports by month")
    if not trends.empty:
        st.plotly_chart(
            charts.line_trend(trends, "year_month", "report_count", title="Reported cases"),
            use_container_width=True,
        )
    panel_end()

    left, right = st.columns(2)
    with left:
        panel_start("Top reported products")
        if not top_drugs.empty:
            st.plotly_chart(
                charts.bar_rank(top_drugs, "reports", "product", title="Medicinal products"),
                use_container_width=True,
            )
        panel_end()
    with right:
        panel_start("Top reported reactions (MedDRA PT)")
        if not top_rxn.empty:
            st.plotly_chart(
                charts.bar_rank(top_rxn, "reports", "reaction", title="Reaction terms"),
                use_container_width=True,
            )
        panel_end()

    panel_start("Seriousness flag profile", "Report-level flags — not confirmed outcomes")
    if not outcomes.empty:
        row = outcomes.iloc[0]
        import pandas as pd

        flags = pd.DataFrame(
            {
                "flag": ["Death", "Hospitalization", "Life-threatening", "Disabling"],
                "reports": [
                    int(row["death_flag"] or 0),
                    int(row["hosp_flag"] or 0),
                    int(row["life_flag"] or 0),
                    int(row["disable_flag"] or 0),
                ],
            }
        )
        st.plotly_chart(
            charts.bar_rank(flags, "reports", "flag", title="Seriousness attributes", orientation="h"),
            use_container_width=True,
        )
    panel_end()

    if len(top_drugs) and len(top_rxn):
        panel_start(
            "Product × reaction heatmap (top overlap)",
            "Counts are distinct report co-occurrences in the loaded sample.",
        )
        import pandas as pd

        heat = da.query(
            """
            SELECT d.medicinalproduct AS product,
                   r.reaction_pt AS reaction,
                   COUNT(DISTINCT d.safetyreportid) AS reports
            FROM dim_reported_drugs d
            JOIN dim_reported_reactions r ON d.safetyreportid = r.safetyreportid
            WHERE d.medicinalproduct IN (
                SELECT medicinalproduct FROM (
                  SELECT medicinalproduct, COUNT(DISTINCT safetyreportid) AS c
                  FROM dim_reported_drugs
                  WHERE medicinalproduct IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
                  GROUP BY 1 ORDER BY c DESC LIMIT 8
                )
            )
            AND r.reaction_pt IN (
                SELECT reaction_pt FROM (
                  SELECT reaction_pt, COUNT(DISTINCT safetyreportid) AS c
                  FROM dim_reported_reactions
                  WHERE reaction_pt IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
                  GROUP BY 1 ORDER BY c DESC LIMIT 8
                )
            )
            AND COALESCE(d.synthetic, FALSE) = FALSE
            GROUP BY 1, 2
            """
        )
        if not heat.empty:
            matrix = heat.pivot(index="product", columns="reaction", values="reports").fillna(0)
            st.plotly_chart(
                charts.heatmap(matrix, title="Co-reporting intensity"),
                use_container_width=True,
            )
        panel_end()

    st.subheader("Exploratory Reporting Odds Ratio")
    st.caption("Minimum-count thresholds apply. Output labeled exploratory_reporting_signal.")
    drug = st.selectbox("Drug", top_drugs["product"].tolist())
    event = st.selectbox("Event", top_rxn["reaction"].tolist())
    if st.button("Compute exploratory ROR", type="primary"):
        total = kpis["reports"]
        with_drug = int(
            da.query(
                "SELECT COUNT(DISTINCT safetyreportid) AS n FROM dim_reported_drugs "
                "WHERE medicinalproduct = ? AND COALESCE(synthetic, FALSE) = FALSE",
                [drug],
            )["n"].iloc[0]
        )
        with_event = int(
            da.query(
                "SELECT COUNT(DISTINCT safetyreportid) AS n FROM dim_reported_reactions "
                "WHERE reaction_pt = ? AND COALESCE(synthetic, FALSE) = FALSE",
                [event],
            )["n"].iloc[0]
        )
        both = int(
            da.query(
                """
                SELECT COUNT(DISTINCT d.safetyreportid) AS n
                FROM dim_reported_drugs d
                JOIN dim_reported_reactions r ON d.safetyreportid = r.safetyreportid
                WHERE d.medicinalproduct = ? AND r.reaction_pt = ?
                  AND COALESCE(d.synthetic, FALSE) = FALSE
                """,
                [drug, event],
            )["n"].iloc[0]
        )
        table = build_drug_event_contingency(
            reports_with_drug_and_event=both,
            reports_with_drug=with_drug,
            reports_with_event=with_event,
            total_reports=total,
        )
        result = reporting_odds_ratio(table, drug=drug, event=event)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("a", table.a)
        m2.metric("b", table.b)
        m3.metric("c", table.c)
        m4.metric("d", table.d)
        st.json(
            {
                "label": result.label,
                "ror": result.ror,
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
                "min_count_ok": result.min_count_ok,
                "notes": result.notes,
            }
        )
