"""CMS utilization ingestion — disabled until schema verification."""

from __future__ import annotations


def run_cms_utilization_extraction(**_kwargs: object) -> None:
    raise NotImplementedError(
        "CMS Part D ingestion is disabled. Inspect the official CMS dataset schema "
        "and enable cms_part_d in configs/sources.yaml before implementing downloads."
    )
