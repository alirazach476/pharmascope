import numpy as np

from pharmascope.statistics.regression import fit_ols
from pharmascope.statistics.safety_signals import ContingencyTable
from pharmascope.statistics.sensitivity_analysis import ror_continuity_sensitivity


def test_ols_perfect_line() -> None:
    x = np.array([[1.0], [2.0], [3.0], [4.0]])
    y = np.array([2.0, 4.0, 6.0, 8.0])
    result = fit_ols(y, x, feature_names=["x"])
    assert abs(result.coefficients["x"] - 2.0) < 1e-8
    assert result.r_squared > 0.999


def test_ror_sensitivity_includes_corrections() -> None:
    table = ContingencyTable(a=5, b=0, c=10, d=100)
    results = ror_continuity_sensitivity(table, corrections=(0.0, 0.5))
    assert results[0].ror is None  # zero cell, no correction
    assert results[1].ror is not None
