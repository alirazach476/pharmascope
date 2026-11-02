"""Anomaly detection helpers.

An anomaly flag means an observation warrants review. It does not prove fraud,
a pricing violation, or a genuine safety event.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


@dataclass(frozen=True)
class AnomalyResult:
    method: str
    n: int
    n_flagged: int
    scores: list[float]
    flags: list[bool]
    notes: list[str]


def robust_zscore_flags(
    values: np.ndarray | list[float],
    *,
    threshold: float = 3.5,
) -> AnomalyResult:
    """Modified z-score using median absolute deviation."""
    arr = np.asarray(values, dtype=float)
    med = np.nanmedian(arr)
    abs_dev = np.abs(arr - med)
    mad = np.nanmedian(abs_dev)
    notes = [
        "Anomaly warrants review only — not proof of fraud or safety event.",
        "Uses robust (MAD-based) z-scores.",
    ]
    scale = mad
    if scale == 0 or np.isnan(scale):
        # Fallback when >50% of points equal the median (MAD collapses to 0)
        scale = float(np.nanmean(abs_dev))
        notes.append("MAD was zero; fell back to mean absolute deviation.")
    if scale == 0 or np.isnan(scale):
        scores = [0.0] * len(arr)
        flags = [False] * len(arr)
        notes.append("No dispersion — no points flagged.")
    else:
        scores_arr = 0.6745 * (arr - med) / scale
        scores = scores_arr.tolist()
        flags = (np.abs(scores_arr) >= threshold).tolist()
    return AnomalyResult(
        method="robust_zscore",
        n=len(arr),
        n_flagged=int(sum(flags)),
        scores=[float(s) if s == s else 0.0 for s in scores],
        flags=flags,
        notes=notes,
    )


def isolation_forest_flags(
    frame: pd.DataFrame,
    feature_cols: list[str],
    *,
    contamination: float = 0.01,
    random_state: int = 42,
) -> AnomalyResult:
    """Isolation Forest over numeric feature columns."""
    missing = [c for c in feature_cols if c not in frame.columns]
    if missing:
        raise KeyError(f"Missing feature columns: {missing}")
    x = frame[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if len(x) < 10:
        return AnomalyResult(
            method="isolation_forest",
            n=len(x),
            n_flagged=0,
            scores=[0.0] * len(x),
            flags=[False] * len(x),
            notes=[
                "Too few rows for Isolation Forest; no flags raised.",
                "Anomaly warrants review only — not proof of fraud or safety event.",
            ],
        )
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
    )
    preds = model.fit_predict(x)
    scores = (-model.score_samples(x)).tolist()  # higher = more anomalous
    flags = (preds == -1).tolist()
    return AnomalyResult(
        method="isolation_forest",
        n=len(x),
        n_flagged=int(sum(flags)),
        scores=[float(s) for s in scores],
        flags=flags,
        notes=[
            "Anomaly warrants review only — not proof of fraud or safety event.",
            f"contamination={contamination}",
        ],
    )


def reporting_volume_zscore(
    monthly_counts: pd.Series,
    *,
    threshold: float = 3.5,
) -> AnomalyResult:
    """Flag unusual reporting volumes with a robust z-score baseline."""
    return robust_zscore_flags(monthly_counts.to_numpy(dtype=float), threshold=threshold)
