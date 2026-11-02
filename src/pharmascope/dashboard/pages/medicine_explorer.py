"""Medicine explorer with search, filters, and product visuals."""

from __future__ import annotations

import streamlit as st

from pharmascope.dashboard import charts, data_access as da
from pharmascope.dashboard.theme import fmt_int, hero, kpi, panel_end, panel_start


def render() -> None:
    hero(
        "Medicine Explorer",
        "Search authentic NDC Directory products and FAERS-reported medicinal names. "
        "Unmatched products are never asserted identical.",
    )
    tables = da.list_tables()
    kpis = da.warehouse_kpis()
    corpus = da.openfda_corpus_totals()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("NDC loaded", fmt_int(kpis["ndc_products"]), "dim_medicine_ndc")
    with c2:
        total = (corpus.get("totals") or {}).get("ndc_products")
        kpi("OpenFDA NDC corpus", fmt_int(total), "Official API total")
    with c3:
        kpi("Labelers loaded", fmt_int(kpis["labelers"]), "Distinct labeler_name")
    with c4:
        kpi("FAERS product names", fmt_int(kpis["distinct_medicinal_products"]), "Reported names")

    q = st.text_input("Search brand / generic / labeler", placeholder="e.g. metformin, amlodipine…")
    limit = st.slider("Result limit", 25, 500, 100)

    if "dim_medicine_ndc" in tables:
        forms = da.query(
            """
            SELECT COALESCE(dosage_form, '(unknown)') AS dosage_form, COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY products DESC LIMIT 15
            """
        )
        routes = da.query(
            """
            SELECT COALESCE(route, '(unknown)') AS route, COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY products DESC LIMIT 12
            """
        )
        labelers = da.query(
            """
            SELECT COALESCE(labeler_name, '(unknown)') AS labeler, COUNT(*) AS products
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1 ORDER BY products DESC LIMIT 12
            """
        )

        a, b = st.columns(2)
        with a:
            panel_start("Dosage form distribution")
            if not forms.empty:
                st.plotly_chart(
                    charts.bar_rank(forms, "products", "dosage_form", title="Products by dosage form"),
                    use_container_width=True,
                )
            panel_end()
        with b:
            panel_start("Top labelers")
            if not labelers.empty:
                st.plotly_chart(
                    charts.treemap(
                        labelers.assign(root="Labelers"),
                        ["root", "labeler"],
                        "products",
                        title="Labeler concentration",
                    ),
                    use_container_width=True,
                )
            panel_end()

        panel_start("Route of administration")
        if not routes.empty:
            st.plotly_chart(
                charts.donut(routes, "route", "products", title="Route mix"),
                use_container_width=True,
            )
        panel_end()

        if q:
            like = f"%{q.lower()}%"
            df = da.query(
                """
                SELECT product_ndc, brand_name, generic_name, labeler_name,
                       dosage_form, route, active_ingredient_names_raw, source_system
                FROM dim_medicine_ndc
                WHERE COALESCE(synthetic, FALSE) = FALSE
                  AND (
                    lower(COALESCE(brand_name,'')) LIKE ?
                    OR lower(COALESCE(generic_name,'')) LIKE ?
                    OR lower(COALESCE(labeler_name,'')) LIKE ?
                  )
                ORDER BY brand_name
                LIMIT ?
                """,
                [like, like, like, limit],
            )
        else:
            df = da.query(
                """
                SELECT product_ndc, brand_name, generic_name, labeler_name,
                       dosage_form, route, active_ingredient_names_raw, source_system
                FROM dim_medicine_ndc
                WHERE COALESCE(synthetic, FALSE) = FALSE
                ORDER BY brand_name
                LIMIT ?
                """,
                [limit],
            )
        panel_start("Product catalog", f"Showing {len(df)} rows from authentic NDC extract")
        st.dataframe(df, use_container_width=True, height=420)
        panel_end()
    elif "dim_reported_drugs" in tables:
        st.info("NDC directory not loaded — showing FAERS medicinalproduct names.")
        df = da.query(
            """
            SELECT medicinalproduct AS product,
                   COUNT(DISTINCT safetyreportid) AS distinct_reports
            FROM dim_reported_drugs
            WHERE medicinalproduct IS NOT NULL
              AND (? = '' OR lower(medicinalproduct) LIKE ?)
              AND COALESCE(synthetic, FALSE) = FALSE
            GROUP BY 1
            ORDER BY distinct_reports DESC
            LIMIT ?
            """,
            [q or "", f"%{(q or '').lower()}%", limit],
        )
        st.plotly_chart(
            charts.bar_rank(df, "distinct_reports", "product", title="Reported products"),
            use_container_width=True,
        )
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No medicine tables available. Ingest openfda_ndc or openfda_events.")
