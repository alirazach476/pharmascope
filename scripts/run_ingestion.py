#!/usr/bin/env python
"""Run ingestion for one or all enabled OpenFDA sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.orchestration.pipeline_runner import PipelineRunner  # noqa: E402

SOURCES = ["openfda_events", "openfda_ndc", "openfda_recalls"]


def main() -> int:
    parser = argparse.ArgumentParser(description="PharmaScope ingestion runner")
    parser.add_argument("--source", choices=SOURCES, default=None)
    parser.add_argument("--all", action="store_true", help="Ingest all OpenFDA sources")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not args.all and not args.source:
        parser.error("Provide --source or --all")

    setup_logging()
    runner = PipelineRunner()
    targets = SOURCES if args.all else [args.source]
    results = []
    ok = True
    for source in targets:
        print(f"=== Ingesting {source} (bounded unless full download enabled) ===")
        result = runner.extract_source(source, limit=args.limit)
        results.append(result)
        if result.get("status") != "success":
            ok = False
    print(json.dumps(results, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
