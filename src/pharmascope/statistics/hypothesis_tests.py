"""Documented hypothesis testing helpers for observational analyses.

Avoid causal language. Choose tests based on design and assumptions, not
because they yield significance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class TestResult:
    test_name: str
    statistic: float
    pvalue: float
    effect_size: float | None
    effect_size_name: str | None
    n: int
    assumptions: list[str]
    warnings: list[str]
    extras: dict[str, Any]


def welch_t_test(x: list[float] | np.ndarray, y: list[float] | np.ndarray) -> TestResult:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    xa = xa[~np.isnan(xa)]
    ya = ya[~np.isnan(ya)]
    stat, p = stats.ttest_ind(xa, ya, equal_var=False)
    # Cohen's d with Welch pooled variance approximation
    nx, ny = len(xa), len(ya)
    vx, vy = np.var(xa, ddof=1), np.var(ya, ddof=1)
    pooled = np.sqrt(((nx - 1) * vx + (ny - 1) * vy) / max(nx + ny - 2, 1))
    d = float((np.mean(xa) - np.mean(ya)) / pooled) if pooled > 0 else None
    return TestResult(
        test_name="welch_t",
        statistic=float(stat),
        pvalue=float(p),
        effect_size=d,
        effect_size_name="cohens_d",
        n=nx + ny,
        assumptions=[
            "Independent observations within groups",
            "Approximately continuous outcomes",
            "Does not assume equal variances",
        ],
        warnings=["Observational comparison — not causal."],
        extras={"n_x": nx, "n_y": ny},
    )


def mann_whitney_u(x: list[float] | np.ndarray, y: list[float] | np.ndarray) -> TestResult:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    xa = xa[~np.isnan(xa)]
    ya = ya[~np.isnan(ya)]
    stat, p = stats.mannwhitneyu(xa, ya, alternative="two-sided")
    return TestResult(
        test_name="mann_whitney_u",
        statistic=float(stat),
        pvalue=float(p),
        effect_size=None,
        effect_size_name=None,
        n=len(xa) + len(ya),
        assumptions=["Independent observations", "Ordinal or continuous outcomes"],
        warnings=["Observational comparison — not causal."],
        extras={},
    )


def chi_square_independence(table: np.ndarray) -> TestResult:
    arr = np.asarray(table, dtype=float)
    if arr.ndim != 2:
        raise ValueError("chi_square_independence expects a 2D contingency table")
    if np.any(arr < 0):
        raise ValueError("Contingency table cannot contain negative counts")
    warnings = []
    if np.any(arr < 5):
        warnings.append(
            "Some expected/observed cells may be sparse; consider Fisher's exact for 2x2."
        )
    stat, p, dof, expected = stats.chi2_contingency(arr)
    # Cramer's V
    n = arr.sum()
    r, k = arr.shape
    cramer = float(np.sqrt(stat / (n * (min(r, k) - 1)))) if n > 0 and min(r, k) > 1 else None
    return TestResult(
        test_name="chi_square_independence",
        statistic=float(stat),
        pvalue=float(p),
        effect_size=cramer,
        effect_size_name="cramers_v",
        n=int(n),
        assumptions=["Independent observations", "Adequate expected cell counts"],
        warnings=warnings + ["Association only — not causation."],
        extras={"dof": int(dof), "expected": expected.tolist()},
    )


def fisher_exact_2x2(table: np.ndarray) -> TestResult:
    arr = np.asarray(table, dtype=float)
    if arr.shape != (2, 2):
        raise ValueError("fisher_exact_2x2 requires a 2x2 table")
    oddsratio, p = stats.fisher_exact(arr)
    return TestResult(
        test_name="fisher_exact",
        statistic=float(oddsratio),
        pvalue=float(p),
        effect_size=float(oddsratio),
        effect_size_name="odds_ratio",
        n=int(arr.sum()),
        assumptions=["Independent observations", "2x2 categorical table"],
        warnings=["Odds ratio is not relative risk."],
        extras={},
    )
