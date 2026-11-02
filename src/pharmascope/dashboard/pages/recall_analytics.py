"""Recall intelligence with timeline and classification visuals."""

from __future__ import annotations

import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start


def render() -> None:
    hero(
        "Recall Intelligence",
        "FDA drug enforcement / recall records from OpenFDA. Do not infer current status "
        "from historical rows without checking the source status field.",
    )
    tables = da.list_tables()
    if "fact_recalls" not in tables:
        st.info(
            "fact_recalls not loaded. Run download + transform for openfda_recalls."
        )
        return

    kpis = da.warehouse_kpis()
    corpus = da.openfda_corpus_totals()
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Recalls loaded", fmt_int(kpis["recalls"]))
    with c2:
        kpi("OpenFDA recall corpus", fmt_int((corpus.get("totals") or {}).get("drug_recalls")))
    with c3:
        firms = da.query(
            "SELECT COUNT(DISTINCT recalling_firm) AS n FROM fact_recalls "
            "WHERE COALESCE(synthetic, FALSE) = FALSE"
        )["n"].iloc[0]
        kpi("Distinct firms", fmt_int(int(firms)))

    summary = da.query(
        """
        SELECT classification, COUNT(*) AS recalls
        FROM fact_recalls
        WHERE COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1 ORDER BY recalls DESC
        """
    )
    trends = da.query(
        """
        SELECT strftime(CAST(report_date AS DATE), '%Y-%m') AS year_month,
               classification,
               COUNT(*) AS recall_count
        FROM fact_recalls
        WHERE report_date IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1, 2 ORDER BY 1
        """
    )
    status = da.query(
        """
        SELECT COALESCE(status, '(unknown)') AS status, COUNT(*) AS recalls
        FROM fact_recalls
        WHERE COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1 ORDER BY recalls DESC
        """
    )
    firms_df = da.query(
        """
        SELECT COALESCE(recalling_firm, '(unknown)') AS firm, COUNT(*) AS recalls
        FROM fact_recalls
        WHERE COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1 ORDER BY recalls DESC LIMIT 15
        """
    )

    a, b = st.columns(2)
    with a:
        panel_start("Classification mix")
        if not summary.empty:
            st.plotly_chart(
                charts.donut(summary, "classification", "recalls", title="Class I / II / III"),
                use_container_width=True,
            )
        panel_end()
    with b:
        panel_start("Status mix")
        if not status.empty:
            st.plotly_chart(
                charts.donut(status, "status", "recalls", title="Reported status values"),
                use_container_width=True,
            )
        panel_end()

    panel_start("Recalls over time by classification")
    if not trends.empty:
        st.plotly_chart(
            charts.line_trend(
                trends,
                "year_month",
                "recall_count",
                color="classification",
                title="Monthly recall volume",
                height=420,
            ),
            use_container_width=True,
        )
    panel_end()

    panel_start("Top recalling firms")
    if not firms_df.empty:
        st.plotly_chart(
            charts.bar_rank(firms_df, "recalls", "firm", title="Firms by recall count"),
            use_container_width=True,
        )
    panel_end()

    firm = st.text_input("Filter recalling firm")
    if firm:
        df = da.query(
            """
            SELECT recall_number, classification, status, report_date,
                   recalling_firm, reason_for_recall, product_description
            FROM fact_recalls
            WHERE lower(COALESCE(recalling_firm,'')) LIKE ?
              AND COALESCE(synthetic, FALSE) = FALSE
            ORDER BY report_date DESC LIMIT 150
            """,
            [f"%{firm.lower()}%"],
        )
    else:
        df = da.query(
            """
            SELECT recall_number, classification, status, report_date,
                   recalling_firm, reason_for_recall, product_description
            FROM fact_recalls
            WHERE COALESCE(synthetic, FALSE) = FALSE
            ORDER BY report_date DESC LIMIT 150
            """
        )
    panel_start("Recall detail table", f"{len(df)} rows")
    st.dataframe(df, use_container_width=True, height=380)
    panel_end()
