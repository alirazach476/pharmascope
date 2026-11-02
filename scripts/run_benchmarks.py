#!/usr/bin/env python
"""Execute the local performance benchmark harness and print the report path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.monitoring.metrics import run_local_benchmarks  # noqa: E402


def main() -> int:
    setup_logging()
    report = run_local_benchmarks()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
