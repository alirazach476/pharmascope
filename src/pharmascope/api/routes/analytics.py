"""Analytics API endpoints backed by DuckDB gold tables."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from pharmascope.api.dependencies import warehouse_dep
from pharmascope.warehouse import queries
from pharmascope.warehouse.connection import DuckDBWarehouse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _table_exists(wh: DuckDBWarehouse, name: str) -> bool:
    tables = wh.query_df("SHOW TABLES")
    return name in set(tables["name"].tolist())


@router.get("/adverse-events/trends")
def ae_trends(wh: DuckDBWarehouse = Depends(warehouse_dep)) -> dict[str, Any]:
    if not _table_exists(wh, "fact_adverse_event_reports"):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "dataset_not_configured",
                "message": (
                    "fact_adverse_event_reports is not loaded. "
                    "Run OpenFDA events extraction and transformations first."
                ),
            },
        )
    df = queries.adverse_event_trends_by_month(wh)
    return {
        "grain": "distinct safetyreportid by receive month",
        "disclaimer": "Reported cases only; not incidence or causation.",
        "data": df.to_dict(orient="records"),
    }


@router.get("/adverse-events/top-reported")
def ae_top_reported(
    limit: int = Query(default=20, ge=1, le=100),
    wh: DuckDBWarehouse = Depends(warehouse_dep),
) -> dict[str, Any]:
    if not _table_exists(wh, "dim_reported_drugs"):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "dataset_not_configured",
                "message": "dim_reported_drugs is not loaded.",
            },
        )
    df = queries.top_reported_medicinal_products(wh, limit=limit)
    return {
        "grain": "distinct safetyreportid per medicinalproduct",
        "disclaimer": "High report counts do not mean a medicine is dangerous.",
        "data": df.to_dict(orient="records"),
    }


@router.get("/recalls/trends")
def recall_trends(wh: DuckDBWarehouse = Depends(warehouse_dep)) -> dict[str, Any]:
    if not _table_exists(wh, "fact_recalls"):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "dataset_not_configured",
                "message": (
                    "fact_recalls is not loaded. Run openfda_recalls ingestion "
                    "and transformations first."
                ),
            },
        )
    df = queries.recall_trends_by_month(wh)
    return {
        "disclaimer": "Historical recall records; verify status fields before conclusions.",
        "data": df.to_dict(orient="records"),
    }


@router.get("/prices/trends")
def price_trends() -> dict[str, Any]:
    return {
        "error": "dataset_not_configured",
        "message": (
            "Price analytics require an official public price dataset to be "
            "configured and ingested. No fabricated price series is returned."
        ),
    }


@router.get("/utilization/trends")
def utilization_trends() -> dict[str, Any]:
    return {
        "error": "dataset_not_configured",
        "message": (
            "Utilization analytics require CMS Part D or another configured "
            "utilization source. Source is disabled until schema inspection completes."
        ),
    }


@router.get("/forecasts")
def forecasts() -> dict[str, Any]:
    return {
        "error": "dataset_not_configured",
        "message": (
            "Forecasts are available only after a verified utilization time series "
            "exists. No invented accuracy metrics are returned."
        ),
    }
