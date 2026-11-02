"""DuckDB warehouse connection management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from pharmascope.config.logging_config import get_logger
from pharmascope.config.settings import Settings, get_settings

logger = get_logger("warehouse.connection")


class DuckDBWarehouse:
    """Local analytical warehouse backed by DuckDB + Parquet."""

    def __init__(self, settings: Settings | None = None, *, read_only: bool = False) -> None:
        self.settings = settings or get_settings()
        self.db_path = self.settings.resolve_duckdb_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
            logger.info("Connected to DuckDB at %s (read_only=%s)", self.db_path, self.read_only)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> DuckDBWarehouse:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def execute(self, sql: str, params: list[Any] | None = None) -> duckdb.DuckDBPyConnection:
        conn = self.connect()
        if params:
            return conn.execute(sql, params)
        return conn.execute(sql)

    def query_df(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        return self.execute(sql, params).fetchdf()

    def register_parquet(self, view_name: str, parquet_path: Path) -> None:
        path = Path(parquet_path).resolve().as_posix()
        # Parameterized path via replacement after validation
        if not Path(parquet_path).exists():
            raise FileNotFoundError(parquet_path)
        safe_name = view_name.replace("'", "")
        self.execute(f"CREATE OR REPLACE VIEW {safe_name} AS SELECT * FROM read_parquet('{path}')")
        logger.info("Registered view %s -> %s", safe_name, path)

    def create_table_from_df(self, table_name: str, df: pd.DataFrame, *, replace: bool = True) -> None:
        conn = self.connect()
        conn.register("_tmp_df", df)
        action = "CREATE OR REPLACE TABLE" if replace else "CREATE TABLE IF NOT EXISTS"
        safe = table_name.replace("'", "")
        conn.execute(f"{action} {safe} AS SELECT * FROM _tmp_df")
        conn.unregister("_tmp_df")
        logger.info("Created table %s (%s rows)", safe, len(df))
