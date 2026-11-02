"""Shared dashboard data access — values come from DuckDB / manifests / OpenFDA meta only."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import yaml

from pharmascope.config.settings import get_settings
from pharmascope.warehouse.connection import DuckDBWarehouse


def list_tables() -> list[str]:
    settings = get_settings()
    db = settings.resolve_duckdb_path()
    if not db.exists():
        return []
    try:
        with DuckDBWarehouse(settings, read_only=True) as wh:
            return wh.query_df("SHOW TABLES")["name"].tolist()
    except Exception:
        return []


def query(sql: str, params: list | None = None) -> pd.DataFrame:
    settings = get_settings()
    with DuckDBWarehouse(settings, read_only=True) as wh:
        return wh.query_df(sql, params)


def table_exists(name: str) -> bool:
    return name in list_tables()


def load_sources_config() -> dict:
    settings = get_settings()
    path = settings.sources_config_path()
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh).get("sources", {})


def latest_manifests(limit: int = 20) -> list[dict]:
    import json

    settings = get_settings()
    d = settings.layer_path("metadata") / "manifests"
    if not d.exists():
        return []
    rows = []
    for path in sorted(d.glob("manifest_*.json"), reverse=True)[:limit]:
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def latest_dq_reports(limit: int = 10) -> list[dict]:
    import json

    settings = get_settings()
    d = settings.project_root / "reports" / "quality"
    if not d.exists():
        return []
    rows = []
    for path in sorted(d.glob("dq_report_*.json"), reverse=True)[:limit]:
        rows.append(json.loads(Path(path).read_text(encoding="utf-8")))
    return rows


@lru_cache(maxsize=1)
def openfda_corpus_totals() -> dict[str, Any]:
    """Fetch OpenFDA meta.results.total for enabled endpoints (live corpus size).

    These are official API totals for the public index — not fabricated KPIs.
    Network failures return an empty dict so the dashboard still renders.
    """
    settings = get_settings()
    endpoints = {
        "adverse_event_reports": "https://api.fda.gov/drug/event.json",
        "ndc_products": "https://api.fda.gov/drug/ndc.json",
        "drug_recalls": "https://api.fda.gov/drug/enforcement.json",
    }
    out: dict[str, Any] = {"ok": False, "totals": {}, "error": None}
    try:
        with httpx.Client(timeout=20.0) as client:
            for key, url in endpoints.items():
                params: dict[str, Any] = {"limit": 1}
                if settings.openfda_api_key:
                    params["api_key"] = settings.openfda_api_key
                resp = client.get(url, params=params)
                resp.raise_for_status()
                total = ((resp.json().get("meta") or {}).get("results") or {}).get("total")
                out["totals"][key] = int(total) if total is not None else None
        out["ok"] = True
    except Exception as exc:  # noqa: BLE001 — dashboard must degrade gracefully
        out["error"] = str(exc)
    return out


def warehouse_kpis() -> dict[str, int]:
    tables = set(list_tables())
    kpis = {
        "reports": 0,
        "reported_drugs": 0,
        "reactions": 0,
        "drug_event_pairs": 0,
        "ndc_products": 0,
        "recalls": 0,
        "distinct_medicinal_products": 0,
        "labelers": 0,
    }
    if "fact_adverse_event_reports" in tables:
        kpis["reports"] = int(
            query(
                "SELECT COUNT(DISTINCT safetyreportid) AS n FROM fact_adverse_event_reports "
                "WHERE COALESCE(synthetic, FALSE) = FALSE"
            )["n"].iloc[0]
        )
    if "dim_reported_drugs" in tables:
        row = query(
            """
            SELECT COUNT(*) AS n,
                   COUNT(DISTINCT medicinalproduct) AS products
            FROM dim_reported_drugs
            WHERE COALESCE(synthetic, FALSE) = FALSE
            """
        ).iloc[0]
        kpis["reported_drugs"] = int(row["n"])
        kpis["distinct_medicinal_products"] = int(row["products"])
    if "dim_reported_reactions" in tables:
        kpis["reactions"] = int(
            query(
                "SELECT COUNT(*) AS n FROM dim_reported_reactions "
                "WHERE COALESCE(synthetic, FALSE) = FALSE"
            )["n"].iloc[0]
        )
    if "fact_reported_drug_events" in tables:
        kpis["drug_event_pairs"] = int(
            query(
                "SELECT COUNT(*) AS n FROM fact_reported_drug_events "
                "WHERE COALESCE(synthetic, FALSE) = FALSE"
            )["n"].iloc[0]
        )
    if "dim_medicine_ndc" in tables:
        row = query(
            """
            SELECT COUNT(*) AS n, COUNT(DISTINCT labeler_name) AS labelers
            FROM dim_medicine_ndc
            WHERE COALESCE(synthetic, FALSE) = FALSE
            """
        ).iloc[0]
        kpis["ndc_products"] = int(row["n"])
        kpis["labelers"] = int(row["labelers"])
    if "fact_recalls" in tables:
        kpis["recalls"] = int(
            query(
                "SELECT COUNT(*) AS n FROM fact_recalls WHERE COALESCE(synthetic, FALSE) = FALSE"
            )["n"].iloc[0]
        )
    return kpis
