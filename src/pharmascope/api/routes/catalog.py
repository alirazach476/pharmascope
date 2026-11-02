"""Scale medicines catalog API (authentic NDC seed + labeled synthetic fill)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from pharmascope.warehouse.scale_catalog import (
    ScaleCatalogNotReadyError,
    breakdown,
    catalog_ready,
    dashboard_bundle,
    get_stats,
    search_medicines,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/status")
def catalog_status() -> dict[str, Any]:
    ready = catalog_ready()
    payload: dict[str, Any] = {
        "ready": ready,
        "label": "authentic_openfda_ndc_seed + synthetic_scale_demo",
    }
    if ready:
        try:
            payload["stats"] = get_stats()
        except ScaleCatalogNotReadyError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        payload["message"] = (
            "Run python scripts/generate_synthetic_medicines.py --target 10000000"
        )
    return payload


@router.get("/stats")
def catalog_stats() -> dict[str, Any]:
    try:
        return get_stats()
    except ScaleCatalogNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/breakdown/{kind}")
def catalog_breakdown(kind: str) -> dict[str, Any]:
    try:
        df = breakdown(kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ScaleCatalogNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"kind": kind, "data": df.to_dict(orient="records")}


@router.get("/dashboard")
def catalog_dashboard() -> dict[str, Any]:
    try:
        return dashboard_bundle()
    except ScaleCatalogNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/medicines")
def catalog_medicines(
    q: str | None = Query(default=None),
    dosage_form: str | None = Query(default=None),
    synthetic: bool | None = Query(default=None),
    source: str | None = Query(
        default=None,
        description="Filter by source_system, e.g. Pakistan_medicines.csv",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    try:
        return search_medicines(
            q=q,
            dosage_form=dosage_form,
            synthetic=synthetic,
            source=source,
            limit=limit,
            offset=offset,
        )
    except ScaleCatalogNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
