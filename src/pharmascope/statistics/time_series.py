"""Time-series helpers with chronological validation (no random splits)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ForecastMetrics:
    mae: float
    rmse: float
    mape: float | None
    n: int


@dataclass(frozen=True)
class BacktestResult:
    method: str
    metrics: ForecastMetrics
    predictions: list[float]
    actuals: list[float]
    notes: list[str]


def validate_time_index(dates: pd.Series) -> dict[str, object]:
    parsed = pd.to_datetime(dates, errors="coerce")
    missing = int(parsed.isna().sum())
    ordered = parsed.dropna().sort_values()
    gaps = []
    if len(ordered) >= 2:
        deltas = ordered.diff().dropna()
        # Flag gaps larger than the median delta * 2
        median = deltas.median()
        if pd.notna(median) and median > pd.Timedelta(0):
            gaps = [
                str(ordered.iloc[i])
                for i, d in enumerate(deltas, start=1)
                if d > median * 2
            ]
    return {
        "n": len(dates),
        "parse_failures": missing,
        "min_date": str(ordered.min()) if len(ordered) else None,
        "max_date": str(ordered.max()) if len(ordered) else None,
        "suspected_gap_starts": gaps[:20],
        "notes": [
            "Reporting practice changes may create apparent trends unrelated to risk."
        ],
    }


def chronological_split(
    values: np.ndarray | list[float],
    *,
    test_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(values, dtype=float)
    if test_size <= 0 or test_size >= len(arr):
        raise ValueError("test_size must be between 1 and len(values)-1")
    return arr[:-test_size], arr[-test_size:]


def naive_forecast(history: np.ndarray, horizon: int) -> np.ndarray:
    if len(history) == 0:
        raise ValueError("history empty")
    return np.repeat(history[-1], horizon)


def seasonal_naive_forecast(history: np.ndarray, horizon: int, season: int = 12) -> np.ndarray:
    if len(history) < season:
        return naive_forecast(history, horizon)
    out = []
    for h in range(1, horizon + 1):
        out.append(history[-season + ((h - 1) % season)])
    return np.asarray(out, dtype=float)


def compute_forecast_metrics(actual: np.ndarray, predicted: np.ndarray) -> ForecastMetrics:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if len(actual) != len(predicted):
        raise ValueError("actual/predicted length mismatch")
    err = actual - predicted
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    nonzero = actual != 0
    mape = (
        float(np.mean(np.abs(err[nonzero] / actual[nonzero])) * 100)
        if nonzero.any()
        else None
    )
    return ForecastMetrics(mae=mae, rmse=rmse, mape=mape, n=len(actual))


def rolling_origin_backtest(
    values: np.ndarray | list[float],
    *,
    horizon: int = 1,
    min_train: int = 6,
    method: str = "naive",
    season: int = 12,
) -> BacktestResult:
    """Expanding-window backtest — never shuffles time."""
    arr = np.asarray(values, dtype=float)
    preds: list[float] = []
    acts: list[float] = []
    notes = [
        "Chronological rolling-origin validation only.",
        "Do not use random train/test splits for time-ordered series.",
    ]
    for end in range(min_train, len(arr) - horizon + 1):
        history = arr[:end]
        actual = arr[end : end + horizon]
        if method == "seasonal_naive":
            pred = seasonal_naive_forecast(history, horizon, season=season)
        else:
            pred = naive_forecast(history, horizon)
        preds.extend(pred.tolist())
        acts.extend(actual.tolist())
    if not acts:
        raise ValueError("Series too short for requested backtest configuration")
    metrics = compute_forecast_metrics(np.asarray(acts), np.asarray(preds))
    return BacktestResult(
        method=method,
        metrics=metrics,
        predictions=preds,
        actuals=acts,
        notes=notes,
    )
