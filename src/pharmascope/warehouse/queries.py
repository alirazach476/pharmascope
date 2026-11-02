"""Parameterized analytical queries over gold-layer tables."""

from __future__ import annotations

import pandas as pd

from pharmascope.warehouse.connection import DuckDBWarehouse


def adverse_event_trends_by_month(wh: DuckDBWarehouse) -> pd.DataFrame:
    """Count distinct safety reports by receive month.

    Grain note: counts unique safetyreportid, not drug-event pairs.
    """
    return wh.query_df(
        """
        SELECT
            strftime(CAST(receivedate AS DATE), '%Y-%m') AS year_month,
            COUNT(DISTINCT safetyreportid) AS report_count
        FROM fact_adverse_event_reports
        WHERE receivedate IS NOT NULL
          AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1
        ORDER BY 1
        """
    )


def top_reported_medicinal_products(wh: DuckDBWarehouse, *, limit: int = 20) -> pd.DataFrame:
    """Top medicinal products by distinct report count (reported cases)."""
    return wh.query_df(
        """
        SELECT
            medicinalproduct,
            COUNT(DISTINCT safetyreportid) AS report_count
        FROM dim_reported_drugs
        WHERE medicinalproduct IS NOT NULL
          AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1
        ORDER BY report_count DESC
        LIMIT ?
        """,
        [limit],
    )


def top_reported_reactions(wh: DuckDBWarehouse, *, limit: int = 20) -> pd.DataFrame:
    return wh.query_df(
        """
        SELECT
            reaction_pt,
            COUNT(DISTINCT safetyreportid) AS report_count
        FROM dim_reported_reactions
        WHERE reaction_pt IS NOT NULL
          AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1
        ORDER BY report_count DESC
        LIMIT ?
        """,
        [limit],
    )


def recall_trends_by_month(wh: DuckDBWarehouse) -> pd.DataFrame:
    return wh.query_df(
        """
        SELECT
            strftime(CAST(report_date AS DATE), '%Y-%m') AS year_month,
            classification,
            COUNT(*) AS recall_count
        FROM fact_recalls
        WHERE report_date IS NOT NULL
          AND COALESCE(synthetic, FALSE) = FALSE
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    )


def pipeline_source_summary(wh: DuckDBWarehouse) -> pd.DataFrame:
    """Summarize available analytical tables if present."""
    tables = wh.query_df("SHOW TABLES")
    return tables
