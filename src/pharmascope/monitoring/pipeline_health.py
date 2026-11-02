"""Summarize pipeline health from extraction manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharmascope.config.settings import Settings, get_settings


def summarize_manifests(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    directory = settings.layer_path("metadata") / "manifests"
    if not directory.exists():
        return {"count": 0, "success": 0, "failed": 0, "partial": 0}
    success = failed = partial = 0
    for path in directory.glob("manifest_*.json"):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        status = data.get("status")
        if status == "success":
            success += 1
        elif status == "failed":
            failed += 1
        elif status == "partial":
            partial += 1
    return {
        "count": success + failed + partial,
        "success": success,
        "failed": failed,
        "partial": partial,
    }
