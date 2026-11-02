"""Exploratory drug safety signal analysis (disproportionality).

IMPORTANT DISCLAIMER
--------------------
Reporting Odds Ratios (ROR) are exploratory measures based on spontaneous
adverse-event reports. They do NOT estimate relative risk, incidence, or
causation. A high report count does not mean a medicine is dangerous.
This module must never be used as clinical decision support.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from pharmascope.statistics.multiple_testing import benjamini_hochberg


@dataclass(frozen=True)
class ContingencyTable:
    """2x2 table for a drug-event pair within a defined reporting universe."""

    a: int  # reports with drug AND event
    b: int  # reports with drug WITHOUT event
    c: int  # reports with event WITHOUT drug
    d: int  # reports with neither

    def as_array(self) -> np.ndarray:
        return np.array([[self.a, self.b], [self.c, self.d]], dtype=float)


@dataclass(frozen=True)
class RORResult:
    drug: str
    event: str
    table: ContingencyTable
    ror: float | None
    ci_lower: float | None
    ci_upper: float | None
    continuity_correction: float
    level: float
    min_count_ok: bool
    notes: list[str]
    label: str = "exploratory_reporting_signal"


def reporting_odds_ratio(
    table: ContingencyTable,
    *,
    drug: str = "",
    event: str = "",
    continuity_correction: float = 0.5,
    level: float = 0.95,
    min_count_a: int = 3,
) -> RORResult:
    """Compute ROR with optional Haldane-Anscombe continuity correction.

    ROR = (a * d) / (b * c)

    Zero cells: if any of a,b,c,d is zero, apply continuity_correction to all
    four cells before estimation (documented Haldane-Anscombe style), unless
    correction is 0 in which case ROR is undefined.
    """
    notes = [
        "Exploratory reporting signal only — not relative risk or causation.",
        "Comparison universe and counting unit must be defined by the caller.",
    ]
    a, b, c, d = table.a, table.b, table.c, table.d
    min_ok = a >= min_count_a

    if min(a, b, c, d) == 0:
        if continuity_correction <= 0:
            notes.append("Zero cell present; ROR undefined without continuity correction.")
            return RORResult(
                drug=drug,
                event=event,
                table=table,
                ror=None,
                ci_lower=None,
                ci_upper=None,
                continuity_correction=continuity_correction,
                level=level,
                min_count_ok=min_ok,
                notes=notes,
            )
        notes.append(
            f"Applied continuity correction of {continuity_correction} to all cells "
            "due to zero counts (Haldane-Anscombe style)."
        )
        a_c = a + continuity_correction
        b_c = b + continuity_correction
        c_c = c + continuity_correction
        d_c = d + continuity_correction
    else:
        a_c, b_c, c_c, d_c = float(a), float(b), float(c), float(d)

    ror = (a_c * d_c) / (b_c * c_c)
    # Woolf logit-interval on log(ROR)
    se = np.sqrt(1 / a_c + 1 / b_c + 1 / c_c + 1 / d_c)
    z = float(stats.norm.ppf(1 - (1 - level) / 2))
    log_ror = np.log(ror)
    lower = float(np.exp(log_ror - z * se))
    upper = float(np.exp(log_ror + z * se))
    notes.append("CI uses Woolf logit method on log(ROR).")

    return RORResult(
        drug=drug,
        event=event,
        table=table,
        ror=float(ror),
        ci_lower=lower,
        ci_upper=upper,
        continuity_correction=continuity_correction,
        level=level,
        min_count_ok=min_ok,
        notes=notes,
    )


def build_drug_event_contingency(
    *,
    reports_with_drug_and_event: int,
    reports_with_drug: int,
    reports_with_event: int,
    total_reports: int,
) -> ContingencyTable:
    """Build a 2x2 table from report-level counts (distinct safetyreportid).

    Counting unit must be the report (or another documented unit) — not
    inflated drug×event pair rows unless explicitly intended.
    """
    a = reports_with_drug_and_event
    b = reports_with_drug - a
    c = reports_with_event - a
    d = total_reports - (a + b + c)
    if min(a, b, c, d) < 0:
        raise ValueError(
            f"Inconsistent contingency inputs produced negative cell: a={a}, b={b}, c={c}, d={d}"
        )
    return ContingencyTable(a=a, b=b, c=c, d=d)


def adjust_signal_pvalues(pvalues: list[float], *, alpha: float = 0.05) -> list[float]:
    """Benjamini–Hochberg adjusted p-values for exploratory screening."""
    return benjamini_hochberg(pvalues, alpha=alpha)
