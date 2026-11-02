"""Validation result models and report writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    INFORMATIONAL = "informational"


class CheckResult(BaseModel):
    source: str
    dataset: str
    check_name: str
    severity: Severity
    records_evaluated: int
    failures_detected: int
    failure_percentage: float
    execution_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    recommended_action: str
    details: dict[str, Any] = Field(default_factory=dict)
    passed: bool = True


class ValidationReport(BaseModel):
    report_id: str
    source: str
    dataset: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def has_critical_failures(self) -> bool:
        return any(
            (not c.passed) and c.severity == Severity.CRITICAL for c in self.checks
        )

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"dq_report_{self.source}_{self.report_id}.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        # Also write a human-readable summary
        summary_path = directory / f"dq_report_{self.source}_{self.report_id}.md"
        lines = [
            f"# Data Quality Report — {self.source} / {self.dataset}",
            "",
            f"Generated: {self.generated_at.isoformat()}",
            f"Checks: {len(self.checks)}",
            f"Critical failures: {self.has_critical_failures}",
            "",
            "| Check | Severity | Evaluated | Failures | % | Passed | Action |",
            "|---|---|---:|---:|---:|---|---|",
        ]
        for c in self.checks:
            lines.append(
                f"| {c.check_name} | {c.severity.value} | {c.records_evaluated} | "
                f"{c.failures_detected} | {c.failure_percentage:.2f} | {c.passed} | "
                f"{c.recommended_action} |"
            )
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> ValidationReport:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
