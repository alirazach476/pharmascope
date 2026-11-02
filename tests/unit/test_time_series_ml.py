import numpy as np
import pandas as pd

from pharmascope.ml.anomaly_detection import robust_zscore_flags
from pharmascope.ml.evaluation import binary_classification_metrics
from pharmascope.statistics.time_series import (
    chronological_split,
    compute_forecast_metrics,
    naive_forecast,
    rolling_origin_backtest,
)


def test_chronological_split_order() -> None:
    train, test = chronological_split([1, 2, 3, 4, 5], test_size=2)
    assert list(train) == [1, 2, 3]
    assert list(test) == [4, 5]


def test_naive_and_metrics() -> None:
    pred = naive_forecast(np.array([10.0, 12.0, 14.0]), 2)
    assert list(pred) == [14.0, 14.0]
    m = compute_forecast_metrics(np.array([14.0, 15.0]), pred)
    assert m.mae == 0.5


def test_rolling_origin_backtest() -> None:
    series = list(range(1, 20))
    bt = rolling_origin_backtest(series, horizon=1, min_train=5, method="naive")
    assert bt.metrics.n > 0
    assert "Chronological" in bt.notes[0]


def test_robust_zscore_flags_outlier() -> None:
    values = [1, 1, 1, 1, 1, 1, 1, 1, 100]
    result = robust_zscore_flags(values, threshold=3.5)
    assert result.n_flagged >= 1
    assert result.flags[-1] is True


def test_classification_metrics_known() -> None:
    # TP=1 FP=1 FN=1 TN=1 -> P=0.5 R=0.5 F1=0.5
    metrics = binary_classification_metrics([1, 1, 0, 0], [1, 0, 1, 0])
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5
