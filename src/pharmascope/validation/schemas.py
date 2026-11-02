"""Lightweight schema expectations for silver-layer entities."""

from __future__ import annotations

from typing import Any

# Required columns for silver adverse-event report grain (one row per safety report)
ADVERSE_EVENT_REPORT_REQUIRED = (
    "safetyreportid",
    "receivedate",
    "source_system",
    "batch_id",
    "ingested_at",
)

# Required columns for reported drug-event bridge (avoids multi-valued mega-table)
REPORTED_DRUG_EVENT_REQUIRED = (
    "safetyreportid",
    "drug_index",
    "event_index",
    "medicinalproduct",
    "reaction_pt",
)

RECALL_REQUIRED = (
    "recall_number",
    "classification",
    "report_date",
    "recalling_firm",
    "source_system",
)

NDC_PRODUCT_REQUIRED = (
    "product_ndc",
    "brand_name",
    "generic_name",
    "labeler_name",
    "source_system",
)


def missing_required_columns(columns: list[str] | set[str], required: tuple[str, ...]) -> list[str]:
    present = set(columns)
    return [c for c in required if c not in present]


def non_null_fraction(values: list[Any]) -> float:
    if not values:
        return 0.0
    non_null = sum(1 for v in values if v is not None and v != "")
    return non_null / len(values)
