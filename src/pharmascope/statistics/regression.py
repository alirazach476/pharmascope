"""Regression helpers with basic diagnostics for observational analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split


@dataclass(frozen=True)
class LinearRegressionResult:
    coefficients: dict[str, float]
    r_squared: float
    adj_r_squared: float
    n: int
    residuals_mean: float
    warnings: list[str]
    extras: dict[str, Any]


@dataclass(frozen=True)
class LogisticRegressionResult:
    coefficients: dict[str, float]
    intercept: float
    auc: float | None
    n: int
    warnings: list[str]


def fit_ols(
    y: np.ndarray | list[float],
    X: np.ndarray | list[list[float]],
    *,
    feature_names: list[str] | None = None,
) -> LinearRegressionResult:
    """Ordinary least squares with an intercept.

    Observational only — coefficients are associations, not causal effects.
    """
    y_arr = np.asarray(y, dtype=float)
    x_arr = np.asarray(X, dtype=float)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(-1, 1)
    if len(y_arr) != len(x_arr):
        raise ValueError("y and X length mismatch")
    names = feature_names or [f"x{i}" for i in range(x_arr.shape[1])]
    x_design = sm.add_constant(x_arr, has_constant="add")
    model = sm.OLS(y_arr, x_design).fit()
    coefs = {"intercept": float(model.params[0])}
    for i, name in enumerate(names):
        coefs[name] = float(model.params[i + 1])
    warnings = ["Observational association only — not causal."]
    if model.rsquared < 0.05:
        warnings.append("Very low R² — limited explanatory power.")
    return LinearRegressionResult(
        coefficients=coefs,
        r_squared=float(model.rsquared),
        adj_r_squared=float(model.rsquared_adj),
        n=int(model.nobs),
        residuals_mean=float(np.mean(model.resid)),
        warnings=warnings,
        extras={"aic": float(model.aic), "bic": float(model.bic)},
    )


def fit_logistic_binary(
    y: np.ndarray | list[int],
    X: np.ndarray | list[list[float]],
    *,
    feature_names: list[str] | None = None,
    random_state: int = 42,
    test_size: float = 0.3,
) -> LogisticRegressionResult:
    """Binary logistic regression with a held-out AUC when both classes exist."""
    y_arr = np.asarray(y)
    x_arr = np.asarray(X, dtype=float)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(-1, 1)
    names = feature_names or [f"x{i}" for i in range(x_arr.shape[1])]
    warnings = ["Observational association only — not causal."]
    auc: float | None = None
    if len(np.unique(y_arr)) < 2:
        warnings.append("Single-class outcome — AUC undefined.")
        clf = LogisticRegression(max_iter=1000, random_state=random_state)
        clf.fit(x_arr, y_arr)
    else:
        x_train, x_test, y_train, y_test = train_test_split(
            x_arr, y_arr, test_size=test_size, random_state=random_state, stratify=y_arr
        )
        clf = LogisticRegression(max_iter=1000, random_state=random_state)
        clf.fit(x_train, y_train)
        if len(np.unique(y_test)) == 2:
            proba = clf.predict_proba(x_test)[:, 1]
            auc = float(roc_auc_score(y_test, proba))
        else:
            warnings.append("Test split lacked both classes — AUC undefined.")
    coefs = {name: float(v) for name, v in zip(names, clf.coef_[0])}
    return LogisticRegressionResult(
        coefficients=coefs,
        intercept=float(clf.intercept_[0]),
        auc=auc,
        n=len(y_arr),
        warnings=warnings,
    )
