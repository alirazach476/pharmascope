"""Incremental gold-layer merge helpers for idempotent pipeline reruns.

Analytical gold tables are keyed by stable *business* identifiers. Re-running
ingestion with overlapping source IDs must not silently multiply counts.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Business keys used for gold upserts (batch_id retained as provenance only)
GOLD_BUSINESS_KEYS: dict[str, list[str]] = {
    "fact_adverse_event_reports": ["safetyreportid"],
    "dim_reported_drugs": ["safetyreportid", "drug_index"],
    "dim_reported_reactions": ["safetyreportid", "event_index"],
    "fact_reported_drug_events": ["safetyreportid", "drug_index", "event_index"],
    "fact_recalls": ["recall_number"],
    "dim_medicine_ndc": ["product_ndc"],
}


@dataclass(frozen=True)
class MergeResult:
    table_name: str
    keys: list[str]
    incoming_rows: int
    existing_rows: int
    merged_rows: int
    rows_updated_or_replaced: int
    rows_inserted: int


def merge_gold_frames(
    existing: pd.DataFrame | None,
    incoming: pd.DataFrame,
    *,
    keys: list[str],
    table_name: str = "",
) -> tuple[pd.DataFrame, MergeResult]:
    """Union ``incoming`` into ``existing`` and deduplicate on business keys.

    Incoming rows win on key collision (``keep='last'`` after concat), so a
    newer extraction updates attributes without duplicating the entity.
    """
    if incoming.empty and (existing is None or existing.empty):
        empty = incoming.copy() if incoming is not None else pd.DataFrame()
        return empty, MergeResult(
            table_name=table_name,
            keys=keys,
            incoming_rows=0,
            existing_rows=0,
            merged_rows=0,
            rows_updated_or_replaced=0,
            rows_inserted=0,
        )

    missing = [k for k in keys if k not in incoming.columns]
    if missing:
        raise KeyError(f"Incoming frame missing merge keys {missing} for {table_name}")

    incoming_rows = len(incoming)
    if existing is None or existing.empty:
        deduped, _ = _dedupe(incoming, keys)
        return deduped, MergeResult(
            table_name=table_name,
            keys=keys,
            incoming_rows=incoming_rows,
            existing_rows=0,
            merged_rows=len(deduped),
            rows_updated_or_replaced=0,
            rows_inserted=len(deduped),
        )

    missing_existing = [k for k in keys if k not in existing.columns]
    if missing_existing:
        raise KeyError(
            f"Existing gold frame missing merge keys {missing_existing} for {table_name}"
        )

    existing_keys = set(map(tuple, existing[keys].astype(str).itertuples(index=False, name=None)))
    incoming_keys = set(map(tuple, incoming[keys].astype(str).itertuples(index=False, name=None)))
    overlap = existing_keys & incoming_keys
    inserted = incoming_keys - existing_keys

    combined = pd.concat([existing, incoming], ignore_index=True, sort=False)
    merged, _ = _dedupe(combined, keys)

    return merged, MergeResult(
        table_name=table_name,
        keys=keys,
        incoming_rows=incoming_rows,
        existing_rows=len(existing),
        merged_rows=len(merged),
        rows_updated_or_replaced=len(overlap),
        rows_inserted=len(inserted),
    )


def _dedupe(df: pd.DataFrame, keys: list[str]) -> tuple[pd.DataFrame, int]:
    before = len(df)
    out = df.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)
    return out, before - len(out)


def business_keys_for(table_name: str) -> list[str]:
    if table_name not in GOLD_BUSINESS_KEYS:
        raise KeyError(
            f"No business keys registered for gold table '{table_name}'. "
            f"Known: {sorted(GOLD_BUSINESS_KEYS)}"
        )
    return list(GOLD_BUSINESS_KEYS[table_name])
