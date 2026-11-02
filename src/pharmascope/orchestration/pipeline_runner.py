"""Local CLI pipeline runner for the OpenFDA vertical slice.

Sequence:
1. Extract (optional if raw already present)
2. Bronze (source-preserving parquet)
3. Silver (flatten + normalize + dedupe + DQ)
4. Gold (analytical tables)
5. Load DuckDB warehouse
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from pharmascope.config.logging_config import get_logger, setup_logging
from pharmascope.config.settings import Settings, get_settings
from pharmascope.ingestion.openfda_events import run_openfda_events_extraction
from pharmascope.ingestion.openfda_ndc import run_openfda_ndc_extraction
from pharmascope.ingestion.openfda_recalls import run_openfda_recalls_extraction
from pharmascope.processing.deduplication import deduplicate_dataframe
from pharmascope.processing.flattening import (
    flatten_envelopes_to_frames,
    flatten_ndc_record,
    flatten_recall_record,
)
from pharmascope.processing.normalization import normalize_medicine_name, normalize_ndc
from pharmascope.storage.filesystem import ensure_layer_dirs
from pharmascope.storage.parquet_store import ParquetStore
from pharmascope.validation.data_quality import DataQualityFramework
from pharmascope.validation.schemas import (
    ADVERSE_EVENT_REPORT_REQUIRED,
    NDC_PRODUCT_REQUIRED,
    RECALL_REQUIRED,
    REPORTED_DRUG_EVENT_REQUIRED,
)
from pharmascope.validation.validation_results import Severity
from pharmascope.warehouse.connection import DuckDBWarehouse
from pharmascope.warehouse.repositories import GoldRepository

logger = get_logger("orchestration.pipeline_runner")


class PipelineRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        setup_logging(self.settings)
        ensure_layer_dirs(self.settings)
        self.store = ParquetStore()
        self.gold_repo = GoldRepository(self.settings)
        self.run_id = str(uuid4())

    def _latest_raw_jsonl(self, source: str) -> Path | None:
        raw_root = self.settings.layer_path("raw") / source
        if not raw_root.exists():
            return None
        files = sorted(raw_root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        # Prefer non-partial
        for f in files:
            if "partial" not in f.name:
                return f
        return files[0] if files else None

    def _read_envelopes(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def extract_source(self, source: str, *, limit: int | None = None) -> dict[str, Any]:
        if source == "openfda_events":
            manifest = run_openfda_events_extraction(limit=limit)
        elif source == "openfda_ndc":
            manifest = run_openfda_ndc_extraction(limit=limit)
        elif source == "openfda_recalls":
            manifest = run_openfda_recalls_extraction(limit=limit)
        else:
            raise ValueError(f"Unsupported source for extraction: {source}")
        return manifest.model_dump(mode="json")

    def promote_events_to_bronze_silver_gold(self, raw_path: Path | None = None) -> dict[str, Any]:
        path = raw_path or self._latest_raw_jsonl("openfda_events")
        if path is None:
            raise FileNotFoundError(
                "No raw openfda_events JSONL found. Run extraction first."
            )
        envelopes = self._read_envelopes(path)
        # Reject synthetic flags from entering production layers silently
        authentic = [e for e in envelopes if not (e.get("_ingestion") or {}).get("synthetic")]
        synthetic_count = len(envelopes) - len(authentic)
        if synthetic_count:
            logger.warning(
                "Excluded %s synthetic envelopes from production promotion",
                synthetic_count,
            )

        # Bronze: preserve envelopes as parquet
        bronze_df = pd.DataFrame(
            {
                "batch_id": [(e.get("_ingestion") or {}).get("batch_id") for e in authentic],
                "ingested_at": [(e.get("_ingestion") or {}).get("ingested_at") for e in authentic],
                "safetyreportid": [
                    (e.get("payload") or {}).get("safetyreportid") for e in authentic
                ],
                "payload_json": [json.dumps(e.get("payload") or {}, ensure_ascii=False) for e in authentic],
                "source_system": ["openfda_events"] * len(authentic),
            }
        )
        bronze_path = (
            self.settings.layer_path("bronze")
            / "openfda_events"
            / f"run_{self.run_id}"
            / "events_bronze.parquet"
        )
        self.store.write_dataframe(bronze_df, bronze_path)

        frames = flatten_envelopes_to_frames(authentic)

        # Normalization columns (retain originals)
        drugs = frames["dim_reported_drugs"]
        if not drugs.empty:
            drugs = drugs.copy()
            drugs["medicinalproduct_normalized"] = drugs["medicinalproduct"].map(
                normalize_medicine_name
            )
            drugs["product_ndc_normalized"] = drugs["product_ndc"].map(normalize_ndc)
            frames["dim_reported_drugs"] = drugs

        # Deduplicate report grain
        reports, removed = deduplicate_dataframe(
            frames["fact_adverse_event_reports"],
            ["safetyreportid", "batch_id"],
        )
        frames["fact_adverse_event_reports"] = reports
        logger.info("Removed %s duplicate adverse-event report rows", removed)

        # Data quality
        dq = DataQualityFramework("openfda_events", "silver_adverse_events")
        dq.check_required_columns(reports, ADVERSE_EVENT_REPORT_REQUIRED)
        dq.check_unique_keys(reports, ["safetyreportid", "batch_id"])
        dq.check_null_percentage(reports, "receivedate", max_null_pct=80.0)
        dq.check_record_count_reconciliation(len(authentic), len(reports), tolerance=removed)
        if not frames["fact_reported_drug_events"].empty:
            dq.check_required_columns(
                frames["fact_reported_drug_events"],
                REPORTED_DRUG_EVENT_REQUIRED,
                severity=Severity.HIGH,
            )
        report = dq.build_report()
        report_dir = self.settings.project_root / "reports" / "quality"
        report.save(report_dir)

        if report.has_critical_failures:
            raise RuntimeError(
                "Critical data-quality failures — refusing gold promotion. "
                f"See reports in {report_dir}"
            )

        # Silver writes
        silver_dir = self.settings.layer_path("silver") / "openfda_events" / f"run_{self.run_id}"
        silver_paths = {}
        for name, df in frames.items():
            p = silver_dir / f"{name}.parquet"
            self.store.write_dataframe(df, p)
            silver_paths[name] = str(p)

        # Gold: incremental upsert on business keys (idempotent across batches)
        gold_written = {}
        merge_stats = {}
        for name, df in frames.items():
            gpath, merge_result = self.gold_repo.upsert_gold_table(name, df)
            gold_written[name] = str(gpath)
            merge_stats[name] = self.gold_repo.merge_summary_dict(merge_result)

        # Load warehouse
        with DuckDBWarehouse(self.settings) as wh:
            loaded = self.gold_repo.load_gold_into_duckdb(wh, list(frames.keys()))

        return {
            "run_id": self.run_id,
            "raw_path": str(path),
            "bronze_path": str(bronze_path),
            "silver_paths": silver_paths,
            "gold_tables": gold_written,
            "gold_merge": merge_stats,
            "duckdb_tables": loaded,
            "dq_report_id": report.report_id,
            "record_counts": {k: len(v) for k, v in frames.items()},
            "finished_at": datetime.now(UTC).isoformat(),
        }

    def promote_recalls(self, raw_path: Path | None = None) -> dict[str, Any]:
        path = raw_path or self._latest_raw_jsonl("openfda_recalls")
        if path is None:
            raise FileNotFoundError("No raw openfda_recalls JSONL found.")
        envelopes = [
            e
            for e in self._read_envelopes(path)
            if not (e.get("_ingestion") or {}).get("synthetic")
        ]
        rows = [flatten_recall_record(e) for e in envelopes]
        df = pd.DataFrame(rows)
        df, removed = deduplicate_dataframe(df, ["recall_number", "batch_id"])
        dq = DataQualityFramework("openfda_recalls", "fact_recalls")
        dq.check_required_columns(df, RECALL_REQUIRED)
        dq.check_unique_keys(df, ["recall_number", "batch_id"])
        if "classification" in df.columns:
            dq.check_allowed_values(
                df,
                "classification",
                {"Class I", "Class II", "Class III"},
                severity=Severity.MEDIUM,
            )
        report = dq.build_report()
        report.save(self.settings.project_root / "reports" / "quality")
        if report.has_critical_failures:
            raise RuntimeError("Critical DQ failures for recalls")
        gold_path, merge_result = self.gold_repo.upsert_gold_table("fact_recalls", df)
        with DuckDBWarehouse(self.settings) as wh:
            self.gold_repo.load_gold_into_duckdb(wh, ["fact_recalls"])
        return {
            "rows": len(df),
            "duplicates_removed": removed,
            "gold_path": str(gold_path),
            "gold_merge": self.gold_repo.merge_summary_dict(merge_result),
            "dq_report_id": report.report_id,
        }

    def promote_ndc(self, raw_path: Path | None = None) -> dict[str, Any]:
        path = raw_path or self._latest_raw_jsonl("openfda_ndc")
        if path is None:
            raise FileNotFoundError("No raw openfda_ndc JSONL found.")
        envelopes = [
            e
            for e in self._read_envelopes(path)
            if not (e.get("_ingestion") or {}).get("synthetic")
        ]
        rows = [flatten_ndc_record(e) for e in envelopes]
        df = pd.DataFrame(rows)
        df["brand_name_normalized"] = df["brand_name"].map(normalize_medicine_name)
        df["generic_name_normalized"] = df["generic_name"].map(normalize_medicine_name)
        df["product_ndc_normalized"] = df["product_ndc"].map(normalize_ndc)
        df, removed = deduplicate_dataframe(df, ["product_ndc", "batch_id"])
        dq = DataQualityFramework("openfda_ndc", "dim_medicine_ndc")
        dq.check_required_columns(df, NDC_PRODUCT_REQUIRED)
        dq.check_unique_keys(df, ["product_ndc", "batch_id"])
        report = dq.build_report()
        report.save(self.settings.project_root / "reports" / "quality")
        if report.has_critical_failures:
            raise RuntimeError("Critical DQ failures for NDC")
        gold_path, merge_result = self.gold_repo.upsert_gold_table("dim_medicine_ndc", df)
        with DuckDBWarehouse(self.settings) as wh:
            self.gold_repo.load_gold_into_duckdb(wh, ["dim_medicine_ndc"])
        return {
            "rows": len(df),
            "duplicates_removed": removed,
            "gold_path": str(gold_path),
            "gold_merge": self.gold_repo.merge_summary_dict(merge_result),
            "dq_report_id": report.report_id,
        }

    def run_vertical_slice(self, *, limit: int = 200) -> dict[str, Any]:
        """End-to-end OpenFDA events slice with optional NDC/recalls if extracted."""
        results: dict[str, Any] = {"run_id": self.run_id}
        results["events_extract"] = self.extract_source("openfda_events", limit=limit)
        results["events_transform"] = self.promote_events_to_bronze_silver_gold()
        return results
