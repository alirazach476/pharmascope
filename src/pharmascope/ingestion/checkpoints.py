"""Checkpoint persistence for idempotent incremental extractions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SourceCheckpoint(BaseModel):
    """Last successful extraction state for a source."""

    source_name: str
    last_success_at: datetime | None = None
    last_skip: int = 0
    last_batch_id: str | None = None
    last_window_start: str | None = None
    last_window_end: str | None = None
    processed_identifiers: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
        self.last_success_at = self.updated_at


class CheckpointStore:
    """Filesystem-backed checkpoint store under data/metadata/checkpoints."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, source_name: str) -> Path:
        safe = source_name.replace("/", "_")
        return self.root / f"{safe}.json"

    def load(self, source_name: str) -> SourceCheckpoint:
        path = self.path_for(source_name)
        if not path.exists():
            return SourceCheckpoint(source_name=source_name)
        data = json.loads(path.read_text(encoding="utf-8"))
        return SourceCheckpoint.model_validate(data)

    def save(self, checkpoint: SourceCheckpoint) -> Path:
        checkpoint.touch()
        path = self.path_for(checkpoint.source_name)
        path.write_text(checkpoint.model_dump_json(indent=2), encoding="utf-8")
        return path
