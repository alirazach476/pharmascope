"""Repository helpers for loading gold tables into DuckDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from pharmascope.config.logging_config import get_logger
from pharmascope.config.settings import Settings, get_settings
from pharmascope.processing.gold_merge import MergeResult, business_keys_for, merge_gold_frames
from pharmascope.storage.parquet_store import ParquetStore
from pharmascope.warehouse.connection import DuckDBWarehouse

logger = get_logger("warehouse.repositories")


class GoldRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.store = ParquetStore()

    def gold_dir(self) -> Path:
        return self.settings.layer_path("gold")

    def read_gold_table(self, name: str) -> pd.DataFrame | None:
        path = self.gold_dir() / f"{name}.parquet"
        if not path.exists():
            return None
        return self.store.read_dataframe(path)

    def write_gold_table(self, name: str, df: pd.DataFrame, *, replace: bool = True) -> Path:
        if df.empty:
            logger.warning("Skipping empty gold table write for %s", name)
        path = self.gold_dir() / f"{name}.parquet"
        if "synthetic" in df.columns and len(df) > 0 and bool(df["synthetic"].all()):
            raise ValueError(
                f"Refusing to write gold table '{name}' composed entirely of synthetic rows. "
                "Synthetic fixtures must stay under data/synthetic_test_fixtures/."
            )
        if not replace and path.exists():
            raise FileExistsError(path)
        self.store.write_dataframe(df, path)
        return path

    def upsert_gold_table(self, name: str, incoming: pd.DataFrame) -> tuple[Path, MergeResult]:
        """Merge ``incoming`` into existing gold parquet using registered business keys."""
        keys = business_keys_for(name)
        existing = self.read_gold_table(name)
        merged, result = merge_gold_frames(
            existing, incoming, keys=keys, table_name=name
        )
        path = self.write_gold_table(name, merged, replace=True)
        logger.info(
            "Gold upsert %s: existing=%s incoming=%s merged=%s inserted=%s replaced=%s",
            name,
            result.existing_rows,
            result.incoming_rows,
            result.merged_rows,
            result.rows_inserted,
            result.rows_updated_or_replaced,
        )
        return path, result

    def load_gold_into_duckdb(
        self, wh: DuckDBWarehouse, names: list[str] | None = None
    ) -> list[str]:
        gold = self.gold_dir()
        loaded: list[str] = []
        paths = (
            list(gold.glob("*.parquet"))
            if names is None
            else [gold / f"{n}.parquet" for n in names]
        )
        for path in paths:
            if not path.exists():
                logger.warning("Gold parquet missing: %s", path)
                continue
            table = path.stem
            wh.create_table_from_df(table, self.store.read_dataframe(path), replace=True)
            loaded.append(table)
        return loaded

    def merge_summary_dict(self, result: MergeResult) -> dict[str, Any]:
        return {
            "table_name": result.table_name,
            "keys": result.keys,
            "incoming_rows": result.incoming_rows,
            "existing_rows": result.existing_rows,
            "merged_rows": result.merged_rows,
            "rows_inserted": result.rows_inserted,
            "rows_updated_or_replaced": result.rows_updated_or_replaced,
        }
