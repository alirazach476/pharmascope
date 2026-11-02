"""Performance benchmark harness for PharmaScope workloads.

Records measured timings only — never invents engine superiority claims.
"""

from __future__ import annotations

import json
import platform
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import duckdb
import pandas as pd

from pharmascope.config.settings import Settings, get_settings


@dataclass
class BenchmarkCaseResult:
    name: str
    engine: str
    rows: int
    duration_seconds: float
    peak_memory_kib: float | None
    notes: list[str]


def _timed(fn: Callable[[], Any]) -> tuple[Any, float, float | None]:
    tracemalloc.start()
    start = time.perf_counter()
    result = fn()
    duration = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, duration, peak / 1024.0


def benchmark_pandas_groupby(df: pd.DataFrame, group_col: str, value_col: str) -> BenchmarkCaseResult:
    def _run() -> pd.DataFrame:
        return df.groupby(group_col, dropna=False)[value_col].count().reset_index(name="n")

    out, duration, peak = _timed(_run)
    return BenchmarkCaseResult(
        name="groupby_count",
        engine="pandas",
        rows=len(df),
        duration_seconds=duration,
        peak_memory_kib=peak,
        notes=[f"result_rows={len(out)}"],
    )


def benchmark_duckdb_groupby(
    df: pd.DataFrame, group_col: str, value_col: str
) -> BenchmarkCaseResult:
    con = duckdb.connect(":memory:")
    con.register("t", df)

    def _run() -> pd.DataFrame:
        return con.execute(
            f'SELECT "{group_col}" AS g, COUNT("{value_col}") AS n FROM t GROUP BY 1'
        ).fetchdf()

    out, duration, peak = _timed(_run)
    con.close()
    return BenchmarkCaseResult(
        name="groupby_count",
        engine="duckdb",
        rows=len(df),
        duration_seconds=duration,
        peak_memory_kib=peak,
        notes=[f"result_rows={len(out)}"],
    )


def benchmark_parquet_roundtrip(df: pd.DataFrame, path: Path) -> list[BenchmarkCaseResult]:
    results: list[BenchmarkCaseResult] = []

    def _write() -> None:
        df.to_parquet(path, index=False)

    _, wdur, wpeak = _timed(_write)
    results.append(
        BenchmarkCaseResult(
            name="parquet_write",
            engine="pandas+pyarrow",
            rows=len(df),
            duration_seconds=wdur,
            peak_memory_kib=wpeak,
            notes=[f"path={path}", f"bytes={path.stat().st_size if path.exists() else 0}"],
        )
    )

    def _read() -> pd.DataFrame:
        return pd.read_parquet(path)

    out, rdur, rpeak = _timed(_read)
    results.append(
        BenchmarkCaseResult(
            name="parquet_read",
            engine="pandas+pyarrow",
            rows=len(out),
            duration_seconds=rdur,
            peak_memory_kib=rpeak,
            notes=[f"path={path}"],
        )
    )
    return results


def run_local_benchmarks(settings: Settings | None = None) -> dict[str, Any]:
    """Benchmark against gold parquet if present; otherwise synthetic labeled data."""
    settings = settings or get_settings()
    gold = settings.layer_path("gold") / "dim_reported_drugs.parquet"
    synthetic = False
    if gold.exists():
        df = pd.read_parquet(gold)
        label = "authentic_gold_dim_reported_drugs"
    else:
        synthetic = True
        df = pd.DataFrame(
            {
                "medicinalproduct": [f"SYN-{i % 50}" for i in range(5000)],
                "safetyreportid": [f"R{i}" for i in range(5000)],
            }
        )
        label = "synthetic_benchmark_only"

    tmp = settings.layer_path("metadata") / "benchmark_tmp.parquet"
    tmp.parent.mkdir(parents=True, exist_ok=True)

    cases = [
        benchmark_pandas_groupby(df, "medicinalproduct", "safetyreportid"),
        benchmark_duckdb_groupby(df, "medicinalproduct", "safetyreportid"),
        *benchmark_parquet_roundtrip(df, tmp),
    ]

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_label": label,
        "synthetic": synthetic,
        "rows": len(df),
        "hardware": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version,
        },
        "warmup": "none (single timed run; interpret cautiously)",
        "cases": [asdict(c) for c in cases],
        "limitations": [
            "Single-run timings without warm-up; variance expected.",
            "Peak memory via tracemalloc is Python-allocator scoped, not RSS.",
            "Spark not started for this small local workload.",
            "Do not generalize engine rankings beyond this measured dataset.",
        ],
    }
    out_dir = settings.project_root / "reports" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "benchmark_latest.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["output_path"] = str(out_path)
    return report
