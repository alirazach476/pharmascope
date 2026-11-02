"""Exploratory data analysis helpers for pharmaceutical analytical tables."""

from __future__ import annotations

from typing import Any

import pandas as pd


def missingness_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return null/empty rates per column."""
    rows = []
    n = len(df)
    for col in df.columns:
        series = df[col]
        nulls = int(series.isna().sum())
        empties = int((series.astype(str).str.strip() == "").sum()) if n else 0
        rows.append(
            {
                "column": col,
                "n": n,
                "null_count": nulls,
                "empty_string_count": empties,
                "missing_pct": round(100.0 * (nulls + empties) / n, 4) if n else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("missing_pct", ascending=False).reset_index(drop=True)


def categorical_frequency(
    df: pd.DataFrame,
    column: str,
    *,
    top_n: int = 25,
) -> pd.DataFrame:
    if column not in df.columns:
        raise KeyError(column)
    counts = (
        df[column]
        .fillna("(missing)")
        .astype(str)
        .value_counts()
        .head(top_n)
        .rename_axis(column)
        .reset_index(name="count")
    )
    counts["share"] = counts["count"] / max(len(df), 1)
    return counts


def coverage_report(
    *,
    source: str,
    table: str,
    df: pd.DataFrame,
    id_column: str | None = None,
) -> dict[str, Any]:
    """Compact coverage metadata for dashboards and audit trails."""
    result: dict[str, Any] = {
        "source": source,
        "table": table,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
    }
    if id_column and id_column in df.columns:
        result["distinct_ids"] = int(df[id_column].nunique(dropna=True))
    if "synthetic" in df.columns:
        result["synthetic_rows"] = int(df["synthetic"].fillna(False).astype(bool).sum())
        result["authentic_rows"] = len(df) - result["synthetic_rows"]
    return result
