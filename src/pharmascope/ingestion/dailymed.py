"""DailyMed client — disabled until bulk/API path verified."""

from __future__ import annotations


def run_dailymed_extraction(**_kwargs: object) -> None:
    raise NotImplementedError(
        "DailyMed ingestion is disabled. Verify official SPL resources and enable "
        "dailymed in configs/sources.yaml before implementing downloads."
    )
