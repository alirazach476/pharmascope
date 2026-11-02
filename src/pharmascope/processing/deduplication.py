"""Deduplication helpers for idempotent pipeline reruns."""

from __future__ import annotations

import pandas as pd


def deduplicate_dataframe(
    df: pd.DataFrame,
    keys: list[str],
    *,
    keep: str = "last",
) -> tuple[pd.DataFrame, int]:
    """Drop duplicate rows by ``keys``.

    Returns the deduplicated frame and the number of rows removed.
    """
    if df.empty:
        return df.copy(), 0
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise KeyError(f"Deduplication keys missing from DataFrame: {missing}")
    before = len(df)
    out = df.drop_duplicates(subset=keys, keep=keep).reset_index(drop=True)
    return out, before - len(out)
