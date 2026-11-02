"""Medicine explorer API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from pharmascope.api.dependencies import warehouse_dep
from pharmascope.warehouse.connection import DuckDBWarehouse

router = APIRouter(prefix="/api/v1/medicines", tags=["medicines"])


def _has_table(wh: DuckDBWarehouse, name: str) -> bool:
    return name in set(wh.query_df("SHOW TABLES")["name"].tolist())


@router.get("")
def list_medicines(
    q: str | None = Query(default=None, description="Search brand or generic name"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    wh: DuckDBWarehouse = Depends(warehouse_dep),
) -> dict[str, Any]:
    if _has_table(wh, "dim_medicine_ndc"):
        if q:
            like = f"%{q.lower()}%"
            df = wh.query_df(
                """
                SELECT product_ndc, brand_name, generic_name, labeler_name,
                       dosage_form, route, source_system
                FROM dim_medicine_ndc
                WHERE lower(COALESCE(brand_name, '')) LIKE ?
                   OR lower(COALESCE(generic_name, '')) LIKE ?
                ORDER BY brand_name
                LIMIT ? OFFSET ?
                """,
                [like, like, limit, offset],
            )
        else:
            df = wh.query_df(
                """
                SELECT product_ndc, brand_name, generic_name, labeler_name,
                       dosage_form, route, source_system
                FROM dim_medicine_ndc
                ORDER BY brand_name
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            )
        return {
            "source": "dim_medicine_ndc",
            "count": len(df),
            "limit": limit,
            "offset": offset,
            "data": df.to_dict(orient="records"),
            "note": "Products are source-specific; unmatched names are not asserted identical.",
        }

    if _has_table(wh, "dim_reported_drugs"):
        df = wh.query_df(
            """
            SELECT medicinalproduct, COUNT(DISTINCT safetyreportid) AS report_count
            FROM dim_reported_drugs
            WHERE medicinalproduct IS NOT NULL
            GROUP BY 1
            ORDER BY report_count DESC
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )
        return {
            "source": "dim_reported_drugs",
            "count": len(df),
            "data": df.to_dict(orient="records"),
            "note": "Reported product names from FAERS — not a complete product catalog.",
        }

    raise HTTPException(
        status_code=404,
        detail={
            "error": "dataset_not_configured",
            "message": "No medicine tables loaded. Ingest openfda_ndc or openfda_events first.",
        },
    )


@router.get("/{medicine_id}")
def get_medicine(
    medicine_id: str,
    wh: DuckDBWarehouse = Depends(warehouse_dep),
) -> dict[str, Any]:
    if not _has_table(wh, "dim_medicine_ndc"):
        raise HTTPException(
            status_code=404,
            detail={"error": "dataset_not_configured", "message": "dim_medicine_ndc not loaded"},
        )
    df = wh.query_df(
        "SELECT * FROM dim_medicine_ndc WHERE product_ndc = ? LIMIT 5",
        [medicine_id],
    )
    if df.empty:
        raise HTTPException(status_code=404, detail={"error": "not_found", "medicine_id": medicine_id})
    return {"data": df.to_dict(orient="records")[0]}
