"""Model evaluation metrics — never invent performance numbers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pharmascope.statistics.time_series import ForecastMetrics, compute_forecast_metrics


@dataclass(frozen=True)
class ClassificationMetrics:
    precision: float
    recall: float
    f1: float
    support_positive: int
    support_negative: int


def binary_classification_metrics(
    y_true: np.ndarray | list[int],
    y_pred: np.ndarray | list[int],
) -> ClassificationMetrics:
    yt = np.asarray(y_true).astype(int)
    yp = np.asarray(y_pred).astype(int)
    tp = int(((yt == 1) & (yp == 1)).sum())
    fp = int(((yt == 0) & (yp == 1)).sum())
    fn = int(((yt == 1) & (yp == 0)).sum())
    tn = int(((yt == 0) & (yp == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )
    return ClassificationMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        support_positive=tp + fn,
        support_negative=tn + fp,
    )


def forecast_metrics(actual: np.ndarray, predicted: np.ndarray) -> ForecastMetrics:
    return compute_forecast_metrics(actual, predicted)
