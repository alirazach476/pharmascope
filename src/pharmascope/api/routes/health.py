"""Health and source registry endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends

from pharmascope import __disclaimer__, __version__
from pharmascope.api.dependencies import settings_dep
from pharmascope.config.settings import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(settings_dep)) -> dict[str, Any]:
    duckdb_exists = settings.resolve_duckdb_path().exists()
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.pharmascope_env,
        "duckdb_configured": True,
        "duckdb_file_exists": duckdb_exists,
        "disclaimer": __disclaimer__,
    }


@router.get("/api/v1/sources")
def list_sources(settings: Settings = Depends(settings_dep)) -> dict[str, Any]:
    path: Path = settings.sources_config_path()
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    sources = data.get("sources", {})
    items = []
    for key, cfg in sources.items():
        items.append(
            {
                "key": key,
                "name": cfg.get("name"),
                "official_url": cfg.get("official_url"),
                "enabled": cfg.get("enabled", False),
                "schema_version": cfg.get("schema_version"),
                "license_terms": cfg.get("license_terms"),
            }
        )
    return {"sources": items}
