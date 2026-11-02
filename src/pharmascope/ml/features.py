"""Feature builders for ML components (explicit, documented columns only)."""

from __future__ import annotations

import pandas as pd


def monthly_report_volume_features(trends: pd.DataFrame) -> pd.DataFrame:
    """Build lag features from a year_month / report_count frame."""
    required = {"year_month", "report_count"}
    if not required.issubset(trends.columns):
        raise KeyError(f"Expected columns {required}, got {list(trends.columns)}")
    df = trends.sort_values("year_month").copy()
    df["report_count"] = pd.to_numeric(df["report_count"], errors="coerce").fillna(0)
    df["lag_1"] = df["report_count"].shift(1)
    df["lag_3"] = df["report_count"].shift(3)
    df["rolling_mean_3"] = df["report_count"].rolling(3, min_periods=1).mean()
    return df
