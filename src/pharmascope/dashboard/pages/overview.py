"""Executive overview — computed KPIs + Plotly visuals."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start


def render() -> None:
    hero(
        "Pharmaceutical Intelligence Overview",
        "Live KPIs from your DuckDB warehouse plus official OpenFDA corpus totals. "
        "Loaded sample counts are authentic extracts — never invented medicine rows.",
        badge="Executive command center",
    )

    kpis = da.warehouse_kpis()
    corpus = da.openfda_corpus_totals()
    tables = da.list_tables()
    manifests = da.latest_manifests(50)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi("AE reports loaded", fmt_int(kpis["reports"]), "Distinct safetyreportid")
    with c2:
        kpi("NDC products loaded", fmt_int(kpis["ndc_products"]), "Warehouse dim_medicine_ndc")
    with c3:
        kpi("Reported products", fmt_int(kpis["distinct_medicinal_products"]), "Distinct FAERS names")
    with c4:
        kpi("Recalls loaded", fmt_int(kpis["recalls"]), "Enforcement records")
    with c5:
        kpi("Drug×event pairs", fmt_int(kpis["drug_event_pairs"]), "Association grain")

    st.markdown("")
    if corpus.get("ok"):
        totals = corpus["totals"]
        panel_start(
            "Official OpenFDA public corpus (API meta.total)",
            "These are live totals published by OpenFDA for the full public index — "
            "not fabricated dashboard numbers. Your warehouse holds a reproducible sample.",
        )
        g1, g2, g3 = st.columns(3)
        with g1:
            kpi(
                "FAERS reports in OpenFDA",
                fmt_int(totals.get("adverse_event_reports")),
                "api.fda.gov/drug/event.json",
            )
        with g2:
            kpi(
                "NDC products in OpenFDA",
                fmt_int(totals.get("ndc_products")),
                "National Drug Code Directory",
            )
        with g3:
            kpi(
                "Recall records in OpenFDA",
                fmt_int(totals.get("drug_recalls")),
                "Drug enforcement endpoint",
            )
        panel_end()
        st.caption(
            "Note: OpenFDA NDC is on the order of hundreds of thousands of products, not "
            "tens of millions. Multi-million scale in this domain usually refers to "
            "adverse-event *reports* (FAERS), which PharmaScope also models."
        )
    elif corpus.get("error"):
        st.warning(f"Could not refresh OpenFDA corpus totals: {corpus['error']}")

    left, right = st.columns((1.4, 1))
    with left:
        panel_start("Adverse-event reporting trend", "Distinct reports by receive month")
        if "fact_adverse_event_reports" in tables:
            trends = da.query(
                """
                SELECT strftime(CAST(receivedate AS DATE), '%Y-%m') AS year_month,
                       COUNT(DISTINCT safetyreportid) AS report_count
                FROM fact_adverse_event_reports
                WHERE receivedate IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
                GROUP BY 1 ORDER BY 1
                """
            )
            if not trends.empty:
                st.plotly_chart(
                    charts.area_trend(
                        trends, "year_month", "report_count", title="Reported cases over time"
                    ),
                    use_container_width=True,
                )
            else:
                st.info("No dated reports in the loaded sample.")
        else:
            st.info("Load openfda_events to populate this chart.")
        panel_end()

    with right:
        panel_start("Pipeline health", "Extraction manifest outcomes")
        success = sum(1 for m in manifests if m.get("status") == "success")
        failed = sum(1 for m in manifests if m.get("status") == "failed")
        partial = sum(1 for m in manifests if m.get("status") == "partial")
        status_df = pd.DataFrame(
            {
                "status": ["success", "failed", "partial"],
                "count": [success, failed, partial],
            }
        )
        status_df = status_df[status_df["count"] > 0]
        if not status_df.empty:
            st.plotly_chart(
                charts.donut(status_df, "status", "count", title="Manifest status mix"),
                use_container_width=True,
            )
        else:
            st.info("No manifests yet.")
        panel_end()

    b1, b2 = st.columns(2)
    with b1:
        panel_start("Top reported medicinal products", "Distinct report counts")
        if "dim_reported_drugs" in tables:
            top = da.query(
                """
                SELECT medicinalproduct AS product,
                       COUNT(DISTINCT safetyreportid) AS reports
                FROM dim_reported_drugs
                WHERE medicinalproduct IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
                GROUP BY 1 ORDER BY reports DESC LIMIT 12
                """
            )
            if not top.empty:
                st.plotly_chart(
                    charts.bar_rank(top, "reports", "product", title="Most-reported products"),
                    use_container_width=True,
                )
        panel_end()
    with b2:
        panel_start("Recall classification mix", "Loaded enforcement sample")
        if "fact_recalls" in tables:
            cls = da.query(
                """
                SELECT classification, COUNT(*) AS recalls
                FROM fact_recalls
                WHERE classification IS NOT NULL AND COALESCE(synthetic, FALSE) = FALSE
                GROUP BY 1 ORDER BY recalls DESC
                """
            )
            if not cls.empty:
                st.plotly_chart(
                    charts.donut(cls, "classification", "recalls", title="Recall classes"),
                    use_container_width=True,
                )
        panel_end()

    panel_start("Source coverage funnel", "From public corpus → configured → loaded sample")
    if corpus.get("ok"):
        ae_total = corpus["totals"].get("adverse_event_reports") or 0
        ndc_total = corpus["totals"].get("ndc_products") or 0
        funnel_vals = [
            max(ae_total, ndc_total),
            ae_total + ndc_total,
            kpis["reports"] + kpis["ndc_products"] + kpis["recalls"],
            kpis["reports"],
        ]
        st.plotly_chart(
            charts.funnel(
                [
                    "Largest OpenFDA index (reports or NDC)",
                    "Sum of AE + NDC corpus totals",
                    "Rows currently loaded (reports+NDC+recalls)",
                    "AE reports in warehouse",
                ],
                funnel_vals,
                title="Coverage perspective (authentic totals only)",
            ),
            use_container_width=True,
        )
    panel_end()
