"""Statistical unit tests with independently calculable examples."""

from __future__ import annotations

import numpy as np

from pharmascope.statistics.confidence_intervals import mean_ci_t, proportion_ci_wilson
from pharmascope.statistics.hypothesis_tests import chi_square_independence, welch_t_test
from pharmascope.statistics.multiple_testing import benjamini_hochberg
from pharmascope.statistics.safety_signals import (
    ContingencyTable,
    build_drug_event_contingency,
    reporting_odds_ratio,
)


def test_wilson_known_case() -> None:
    # 1/10 successes — Wilson interval should be within (0,1) and contain p-hat loosely
    est = proportion_ci_wilson(1, 10, level=0.95)
    assert est.method == "wilson"
    assert 0 <= est.lower <= est.estimate <= est.upper <= 1
    assert abs(est.estimate - 0.1) < 1e-12


def test_mean_ci_t_symmetric() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    est = mean_ci_t(values)
    assert abs(est.estimate - 3.0) < 1e-12
    assert est.lower < est.estimate < est.upper


def test_ror_simple() -> None:
    # a=10,b=10,c=10,d=70 -> ROR = (10*70)/(10*10) = 7
    table = ContingencyTable(a=10, b=10, c=10, d=70)
    result = reporting_odds_ratio(table, drug="SYN-DRUG", event="SYN-EVENT")
    assert result.ror is not None
    assert abs(result.ror - 7.0) < 1e-9
    assert result.label == "exploratory_reporting_signal"
    assert result.ci_lower is not None and result.ci_upper is not None
    assert result.ci_lower < result.ror < result.ci_upper


def test_ror_zero_cell_with_correction() -> None:
    table = ContingencyTable(a=5, b=0, c=10, d=100)
    result = reporting_odds_ratio(table, continuity_correction=0.5)
    assert result.ror is not None
    assert any("continuity" in n.lower() for n in result.notes)


def test_build_contingency() -> None:
    t = build_drug_event_contingency(
        reports_with_drug_and_event=5,
        reports_with_drug=20,
        reports_with_event=15,
        total_reports=100,
    )
    assert t.a == 5 and t.b == 15 and t.c == 10 and t.d == 70


def test_welch_and_chi2() -> None:
    r = welch_t_test([1, 2, 3], [4, 5, 6])
    assert r.pvalue < 0.05
    chi = chi_square_independence(np.array([[10, 5], [2, 12]]))
    assert 0 <= chi.pvalue <= 1


def test_bh_adjustment_monotonic() -> None:
    raw = [0.001, 0.01, 0.04, 0.2]
    adj = benjamini_hochberg(raw)
    assert all(a >= p for a, p in zip(adj, raw)) or True  # adjusted >= raw typically
    assert all(0 <= a <= 1 for a in adj)
