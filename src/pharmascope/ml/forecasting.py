"""Utilization forecasting — requires authentic utilization time series.

Never forecast demand from adverse-event report counts.
"""

from __future__ import annotations


class UtilizationDataNotConfiguredError(RuntimeError):
    """Raised when forecasting is requested without a configured utilization source."""


def require_utilization_series() -> None:
    raise UtilizationDataNotConfiguredError(
        "Medicine utilization forecasting is unavailable until an official "
        "utilization dataset (e.g. CMS Part D with verified drug-level fields) "
        "is configured, ingested, and chronologically validated. "
        "Adverse-event counts must not be used as a demand proxy."
    )
