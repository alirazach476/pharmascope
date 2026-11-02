"""Named pipeline jobs used by CLI and optional Airflow wrappers."""

from __future__ import annotations

from typing import Any

from pharmascope.orchestration.pipeline_runner import PipelineRunner


def job_extract(source: str, limit: int | None = None) -> dict[str, Any]:
    return PipelineRunner().extract_source(source, limit=limit)


def job_transform(source: str) -> dict[str, Any]:
    runner = PipelineRunner()
    if source == "openfda_events":
        return runner.promote_events_to_bronze_silver_gold()
    if source == "openfda_recalls":
        return runner.promote_recalls()
    if source == "openfda_ndc":
        return runner.promote_ndc()
    raise ValueError(f"Unsupported transform source: {source}")


def job_vertical_slice(limit: int = 200) -> dict[str, Any]:
    return PipelineRunner().run_vertical_slice(limit=limit)
