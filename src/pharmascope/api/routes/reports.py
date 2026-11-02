"""Statistical and data-quality report endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from pharmascope.api.dependencies import settings_dep
from pharmascope.config.settings import Settings

router = APIRouter(prefix="/api/v1", tags=["reports"])


@router.get("/reports/statistical")
def statistical_reports(settings: Settings = Depends(settings_dep)) -> dict[str, Any]:
    path = settings.project_root / "reports" / "statistical" / "analytics_summary.json"
    if not path.exists():
        return {
            "error": "report_not_found",
            "message": "Run scripts/run_analytics.py after loading gold tables.",
            "expected_path": str(path),
        }
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/data-quality/summary")
def data_quality_summary(settings: Settings = Depends(settings_dep)) -> dict[str, Any]:
    dq_dir = settings.project_root / "reports" / "quality"
    if not dq_dir.exists():
        return {"reports": [], "message": "No data-quality reports found yet."}
    reports = []
    for path in sorted(dq_dir.glob("dq_report_*.json"), reverse=True)[:20]:
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    return {"reports": reports, "count": len(reports)}


@router.get("/pipeline/runs")
def pipeline_runs(settings: Settings = Depends(settings_dep)) -> dict[str, Any]:
    manifest_dir = settings.layer_path("metadata") / "manifests"
    if not manifest_dir.exists():
        return {"runs": [], "message": "No extraction manifests found."}
    runs = []
    for path in sorted(manifest_dir.glob("manifest_*.json"), reverse=True)[:50]:
        runs.append(json.loads(Path(path).read_text(encoding="utf-8")))
    return {"runs": runs, "count": len(runs)}
