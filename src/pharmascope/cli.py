"""PharmaScope command-line interface."""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich import print as rprint

from pharmascope.config.logging_config import setup_logging
from pharmascope.config.settings import get_settings
from pharmascope.orchestration.pipeline_runner import PipelineRunner

app = typer.Typer(help="PharmaScope pharmaceutical data intelligence CLI")


@app.command("download")
def download(
    source: str = typer.Option(..., help="Source key, e.g. openfda_events"),
    limit: Optional[int] = typer.Option(
        None,
        help="Max records (defaults to PHARMASCOPE_DEV_RECORD_LIMIT)",
    ),
) -> None:
    """Download a bounded sample from an official source API."""
    setup_logging()
    runner = PipelineRunner()
    result = runner.extract_source(source, limit=limit)
    rprint(json.dumps(result, indent=2, default=str))


@app.command("transform")
def transform(
    source: str = typer.Option(
        "openfda_events",
        help="Source to promote through bronze/silver/gold",
    ),
) -> None:
    """Transform latest raw extraction into analytical layers."""
    setup_logging()
    runner = PipelineRunner()
    if source == "openfda_events":
        result = runner.promote_events_to_bronze_silver_gold()
    elif source == "openfda_recalls":
        result = runner.promote_recalls()
    elif source == "openfda_ndc":
        result = runner.promote_ndc()
    else:
        raise typer.BadParameter(f"Unsupported source: {source}")
    rprint(json.dumps(result, indent=2, default=str))


@app.command("run-slice")
def run_slice(
    limit: int = typer.Option(200, help="Bounded extraction size for the vertical slice"),
) -> None:
    """Run the OpenFDA adverse-events vertical slice end to end."""
    setup_logging()
    settings = get_settings()
    rprint(
        f"[bold]PharmaScope vertical slice[/bold] env={settings.pharmascope_env} "
        f"limit={limit} (bounded_sample unless ALLOW_FULL_DOWNLOAD)"
    )
    runner = PipelineRunner(settings)
    result = runner.run_vertical_slice(limit=limit)
    rprint(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    app()
