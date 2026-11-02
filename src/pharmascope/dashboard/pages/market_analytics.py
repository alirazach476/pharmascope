"""Market / product landscape visuals from NDC + reporting overlap."""

from __future__ import annotations

import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start


def render() -> None:
    hero(
        "Market & Product Landscape",
        "Product-form and labeler analytics from the NDC Directory sample. "
        "Price/utilization charts appear only when those official datasets are configured.",
    )
    tables = da.list_tables()
    kpis = da.warehouse_kpis()
    corpus = da.openfda_corpus_totals()

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("NDC products loaded", fmt_int(kpis["ndc_products"]))
    with c2:
        kpi("OpenFDA NDC corpus", fmt_int((corpus.get("totals") or {}).get("ndc_products")))
    with c3:
        kpi("Labelers", fmt_int(kpis["labelers"]))

    if "dim_medicine_ndc" in tables:
        by_type = da.query(
            """
            SELECT COALESCE(product_type, '(unknown)') AS product_type, COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY products DESC
            """
        )
        by_form = da.query(
            """
            SELECT COALESCE(dosage_form, '(unknown)') AS dosage_form, COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY products DESC LIMIT 20
            """
        )
        by_marketing = da.query(
            """
            SELECT COALESCE(marketing_category, '(unknown)') AS marketing_category,
                   COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY products DESC LIMIT 15
            """
        )
        bubble = da.query(
            """
            SELECT COALESCE(labeler_name, '(unknown)') AS labeler,
                   COALESCE(dosage_form, '(unknown)') AS dosage_form,
                   COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1, 2
            ORDER BY products DESC
            LIMIT 40
            """
        )

        a, b = st.columns(2)
        with a:
            panel_start("Product type mix")
            st.plotly_chart(
                charts.donut(by_type, "product_type", "products", title="NDC product types"),
                use_container_width=True,
            )
            panel_end()
        with b:
            panel_start("Marketing category")
            st.plotly_chart(
                charts.bar_rank(
                    by_marketing, "products", "marketing_category", title="Marketing categories"
                ),
                use_container_width=True,
            )
            panel_end()

        panel_start("Dosage form landscape")
        st.plotly_chart(
            charts.treemap(
                by_form.assign(root="Dosage forms"),
                ["root", "dosage_form"],
                "products",
                title="Forms by product count",
            ),
            use_container_width=True,
        )
        panel_end()

        if not bubble.empty:
            panel_start("Labeler × dosage-form concentration")
            st.plotly_chart(
                charts.scatter_bubble(
                    bubble,
                    "labeler",
                    "dosage_form",
                    "products",
                    "labeler",
                    title="Bubble size = product count",
                    height=480,
                ),
                use_container_width=True,
            )
            panel_end()
    else:
        st.info("Ingest openfda_ndc to unlock product landscape charts.")

    st.subheader("Price & utilization")
    if "fact_medicine_prices" in tables:
        st.dataframe(da.query("SELECT * FROM fact_medicine_prices LIMIT 200"), use_container_width=True)
    else:
        st.info(
            "No price dataset configured — charts intentionally omitted rather than fabricated."
        )
    if "fact_medicine_utilization" not in tables:
        st.info(
            "CMS Part D / utilization source is disabled until schema verification. "
            "Adverse-event volume is not a demand forecast."
        )
