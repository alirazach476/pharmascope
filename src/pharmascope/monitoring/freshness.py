"""Data freshness checks from extraction manifests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pharmascope.config.settings import Settings, get_settings


def latest_success_by_source(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    directory = settings.layer_path("metadata") / "manifests"
    latest: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return {"sources": {}, "generated_at": datetime.now(UTC).isoformat()}
    for path in directory.glob("manifest_*.json"):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("status") != "success":
            continue
        source = data.get("source_name")
        finished = data.get("finished_at")
        if not source or not finished:
            continue
        prev = latest.get(source)
        if prev is None or finished > prev.get("finished_at", ""):
            latest[source] = {
                "finished_at": finished,
                "raw_record_count": data.get("raw_record_count"),
                "manifest_id": data.get("manifest_id"),
                "extraction_mode": data.get("extraction_mode"),
            }
    return {"sources": latest, "generated_at": datetime.now(UTC).isoformat()}


def freshness_ages_hours(settings: Settings | None = None) -> dict[str, float | None]:
    payload = latest_success_by_source(settings)
    now = datetime.now(UTC)
    ages: dict[str, float | None] = {}
    for source, meta in payload["sources"].items():
        finished = meta.get("finished_at")
        try:
            ts = datetime.fromisoformat(str(finished).replace("Z", "+00:00"))
            ages[source] = round((now - ts).total_seconds() / 3600.0, 3)
        except ValueError:
            ages[source] = None
    return ages
