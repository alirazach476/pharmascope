#!/usr/bin/env python
"""Download bounded samples from official pharmaceutical data sources.

Examples (PowerShell / bash)::

    python scripts/download_data.py --source openfda_events --limit 500
    python scripts/download_data.py --source openfda_ndc --limit 200
    python scripts/download_data.py --source openfda_recalls --limit 200

By default this performs a *bounded_sample* extraction capped by
PHARMASCOPE_DEV_RECORD_LIMIT. Full downloads require
PHARMASCOPE_ALLOW_FULL_DOWNLOAD=true.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without editable install
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.orchestration.pipeline_runner import PipelineRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="PharmaScope data download")
    parser.add_argument(
        "--source",
        required=True,
        choices=["openfda_events", "openfda_ndc", "openfda_recalls"],
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max records (bounded by dev limit unless full download allowed)",
    )
    args = parser.parse_args()
    setup_logging()
    runner = PipelineRunner()
    result = runner.extract_source(args.source, limit=args.limit)
    print(json.dumps(result, indent=2, default=str))
    status = result.get("status")
    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
