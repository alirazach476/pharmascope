"""Parquet read/write helpers for analytical layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from pharmascope.config.logging_config import get_logger

logger = get_logger("storage.parquet_store")


class ParquetStore:
    """Thin wrapper around PyArrow Parquet for layer persistence."""

    def write_dataframe(
        self,
        df: pd.DataFrame,
        path: Path,
        *,
        partition_cols: list[str] | None = None,
    ) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(df, preserve_index=False)
        if partition_cols:
            pq.write_to_dataset(table, root_path=str(path), partition_cols=partition_cols)
            logger.info("Wrote partitioned parquet dataset to %s (%s rows)", path, len(df))
        else:
            pq.write_table(table, path)
            logger.info("Wrote parquet file %s (%s rows)", path, len(df))
        return path

    def read_dataframe(self, path: Path, **kwargs: Any) -> pd.DataFrame:
        path = Path(path)
        if path.is_dir():
            return pq.read_table(path, **kwargs).to_pandas()
        return pq.read_table(path, **kwargs).to_pandas()

    def read_jsonl_envelopes(self, path: Path) -> pd.DataFrame:
        """Read JSONL ingestion envelopes into a DataFrame of raw payloads + meta."""
        import json

        rows: list[dict[str, Any]] = []
        with Path(path).open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        if not rows:
            return pd.DataFrame(columns=["_ingestion", "payload"])
        return pd.DataFrame(rows)
