#!/usr/bin/env python
"""Initialize DuckDB and load available gold parquet tables."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.config.settings import get_settings  # noqa: E402
from pharmascope.warehouse.connection import DuckDBWarehouse  # noqa: E402
from pharmascope.warehouse.repositories import GoldRepository  # noqa: E402


def main() -> int:
    setup_logging()
    settings = get_settings()
    repo = GoldRepository(settings)
    with DuckDBWarehouse(settings) as wh:
        loaded = repo.load_gold_into_duckdb(wh)
        print(f"DuckDB path: {settings.resolve_duckdb_path()}")
        print(f"Loaded tables: {loaded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
