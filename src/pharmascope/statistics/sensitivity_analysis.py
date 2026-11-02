"""Sensitivity helpers for exploratory safety-signal analyses."""

from __future__ import annotations

from dataclasses import dataclass

from pharmascope.statistics.safety_signals import ContingencyTable, reporting_odds_ratio


@dataclass(frozen=True)
class RORSensitivity:
    continuity_correction: float
    min_count_a: int
    ror: float | None
    ci_lower: float | None
    ci_upper: float | None
    min_count_ok: bool


def ror_continuity_sensitivity(
    table: ContingencyTable,
    *,
    corrections: tuple[float, ...] = (0.0, 0.5, 1.0),
    min_count_a: int = 3,
) -> list[RORSensitivity]:
    """Recompute ROR under alternative continuity corrections."""
    results: list[RORSensitivity] = []
    for corr in corrections:
        out = reporting_odds_ratio(
            table,
            continuity_correction=corr,
            min_count_a=min_count_a,
        )
        results.append(
            RORSensitivity(
                continuity_correction=corr,
                min_count_a=min_count_a,
                ror=out.ror,
                ci_lower=out.ci_lower,
                ci_upper=out.ci_upper,
                min_count_ok=out.min_count_ok,
            )
        )
    return results
