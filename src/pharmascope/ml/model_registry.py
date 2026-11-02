"""Lightweight filesystem model artifact registry."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pharmascope.config.settings import Settings, get_settings


class ModelRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.root = self.settings.resolve_data_root() / "metadata" / "model_registry"
        self.root.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        *,
        name: str,
        task: str,
        metrics: dict[str, Any],
        params: dict[str, Any],
        notes: list[str] | None = None,
    ) -> Path:
        artifact = {
            "model_id": str(uuid4()),
            "name": name,
            "task": task,
            "created_at": datetime.now(UTC).isoformat(),
            "metrics": metrics,
            "params": params,
            "notes": notes or [],
            "disclaimer": (
                "Metrics must be computed from real evaluation runs. "
                "Do not invent accuracy figures."
            ),
        }
        path = self.root / f"{name}_{artifact['model_id']}.json"
        path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return path
