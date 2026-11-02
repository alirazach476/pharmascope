#!/usr/bin/env python
"""Promote raw extractions through bronze → silver → gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.orchestration.pipeline_runner import PipelineRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="PharmaScope transformations")
    parser.add_argument(
        "--source",
        choices=["openfda_events", "openfda_ndc", "openfda_recalls", "all"],
        default="openfda_events",
    )
    args = parser.parse_args()
    setup_logging()
    runner = PipelineRunner()
    results = {}
    sources = (
        ["openfda_events", "openfda_ndc", "openfda_recalls"]
        if args.source == "all"
        else [args.source]
    )
    for source in sources:
        if source == "openfda_events":
            results[source] = runner.promote_events_to_bronze_silver_gold()
        elif source == "openfda_recalls":
            results[source] = runner.promote_recalls()
        elif source == "openfda_ndc":
            results[source] = runner.promote_ndc()
    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
