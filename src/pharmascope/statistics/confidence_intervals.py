"""Confidence interval helpers.

Choose methods appropriate to the estimand. Wilson score intervals are preferred
for proportions over Wald/normal approximations, especially with sparse counts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class IntervalEstimate:
    estimate: float
    lower: float
    upper: float
    level: float
    method: str
    n: int
    notes: str = ""


def mean_ci_t(
    values: np.ndarray | list[float],
    *,
    level: float = 0.95,
) -> IntervalEstimate:
    """Student-t confidence interval for a mean (independent observations)."""
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n < 2:
        raise ValueError("mean_ci_t requires at least 2 observations")
    mean = float(np.mean(arr))
    se = float(np.std(arr, ddof=1) / np.sqrt(n))
    alpha = 1 - level
    tcrit = float(stats.t.ppf(1 - alpha / 2, df=n - 1))
    return IntervalEstimate(
        estimate=mean,
        lower=mean - tcrit * se,
        upper=mean + tcrit * se,
        level=level,
        method="student_t",
        n=n,
    )


def proportion_ci_wilson(
    successes: int,
    n: int,
    *,
    level: float = 0.95,
) -> IntervalEstimate:
    """Wilson score confidence interval for a binomial proportion."""
    if n <= 0:
        raise ValueError("n must be positive")
    if successes < 0 or successes > n:
        raise ValueError("successes must be in [0, n]")
    alpha = 1 - level
    z = float(stats.norm.ppf(1 - alpha / 2))
    phat = successes / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    half = (z / denom) * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return IntervalEstimate(
        estimate=phat,
        lower=float(max(0.0, center - half)),
        upper=float(min(1.0, center + half)),
        level=level,
        method="wilson",
        n=n,
        notes="Prefer Wilson over Wald for sparse proportions.",
    )
