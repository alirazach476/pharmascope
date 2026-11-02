"""Extraction manifests recording provenance for every ingestion run."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ExtractionStatus = Literal[
    "pending",
    "running",
    "success",
    "partial",
    "failed",
    "cancelled",
]


class ExtractionManifest(BaseModel):
    """Structured provenance record for one extraction run."""

    manifest_id: str = Field(default_factory=lambda: str(uuid4()))
    source_name: str
    official_url: str | None = None
    api_endpoint: str | None = None
    license_terms: str | None = None
    data_format: str = "json"
    schema_version: str | None = None

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    status: ExtractionStatus = "pending"

    query_parameters: dict[str, Any] = Field(default_factory=dict)
    page_count: int = 0
    raw_record_count: int = 0
    output_paths: list[str] = Field(default_factory=list)
    checksum_sha256: str | None = None

    extraction_mode: str = "bounded_sample"  # bounded_sample | incremental | full
    error_details: str | None = None
    notes: list[str] = Field(default_factory=list)
    synthetic: bool = False

    def mark_running(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(UTC)

    def mark_finished(
        self,
        *,
        status: ExtractionStatus,
        error_details: str | None = None,
    ) -> None:
        self.status = status
        self.finished_at = datetime.now(UTC)
        if error_details:
            self.error_details = error_details

    def add_output(self, path: Path) -> None:
        self.output_paths.append(str(path))

    def compute_checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        self.checksum_sha256 = digest.hexdigest()
        return self.checksum_sha256

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"manifest_{self.source_name}_{self.manifest_id}.json"
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> ExtractionManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)
