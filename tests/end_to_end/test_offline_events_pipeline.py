"""Offline end-to-end test using SYNTHETIC fixtures only (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from pharmascope.config.settings import Settings, clear_settings_cache
from pharmascope.processing.deduplication import deduplicate_dataframe
from pharmascope.processing.flattening import flatten_envelopes_to_frames
from pharmascope.storage.parquet_store import ParquetStore
from pharmascope.validation.data_quality import DataQualityFramework
from pharmascope.validation.schemas import ADVERSE_EVENT_REPORT_REQUIRED
from pharmascope.warehouse.connection import DuckDBWarehouse


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "synthetic_test_fixtures"
    / "openfda_events_sample.jsonl"
)


def test_offline_flatten_dq_parquet_duckdb(tmp_path: Path, monkeypatch) -> None:
    assert FIXTURE.exists(), "Synthetic fixture missing"
    envelopes = [
        json.loads(line)
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(e["_ingestion"]["synthetic"] is True for e in envelopes)

    frames = flatten_envelopes_to_frames(envelopes)
    reports, removed = deduplicate_dataframe(
        frames["fact_adverse_event_reports"], ["safetyreportid", "batch_id"]
    )
    assert removed == 0
    assert len(reports) == 2
    # Report1: 1 drug × 2 events = 2; Report2: 2 drugs × 1 event = 2
    assert len(frames["fact_reported_drug_events"]) == 4

    dq = DataQualityFramework("synthetic_fixture", "events")
    dq.check_required_columns(reports, ADVERSE_EVENT_REPORT_REQUIRED)
    dq.check_unique_keys(reports, ["safetyreportid", "batch_id"])
    assert not dq.build_report().has_critical_failures

    store = ParquetStore()
    out = tmp_path / "synthetic" / "fact_adverse_event_reports.parquet"
    store.write_dataframe(reports, out)
    roundtrip = store.read_dataframe(out)
    assert len(roundtrip) == 2

    clear_settings_cache()
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "test.duckdb"))
    monkeypatch.setenv("PHARMASCOPE_DATA_ROOT", str(tmp_path / "data"))
    settings = Settings()
    with DuckDBWarehouse(settings) as wh:
        wh.create_table_from_df("fact_adverse_event_reports", roundtrip)
        df = wh.query_df(
            "SELECT COUNT(DISTINCT safetyreportid) AS n FROM fact_adverse_event_reports"
        )
        assert int(df["n"].iloc[0]) == 2
    clear_settings_cache()
