"""Flattening tests use SYNTHETIC fixtures only — not authentic observations."""

from pharmascope.processing.flattening import flatten_adverse_event_report
from pharmascope.processing.normalization import normalize_medicine_name, normalize_ndc


def _synthetic_envelope() -> dict:
    return {
        "_ingestion": {
            "source": "openfda_events",
            "batch_id": "synthetic-batch",
            "ingested_at": "2024-01-01T00:00:00+00:00",
            "synthetic": True,
        },
        "payload": {
            "safetyreportid": "SYN-001",
            "receivedate": "20240115",
            "serious": "1",
            "patient": {
                "patientsex": "1",
                "drug": [
                    {
                        "medicinalproduct": "SYNTHETICILLIN",
                        "drugcharacterization": "1",
                        "openfda": {"brand_name": ["Syntheticillin"], "product_ndc": ["0001-0001"]},
                    }
                ],
                "reaction": [{"reactionmeddrapt": "Synthetic headache", "reactionoutcome": "1"}],
            },
        },
    }


def test_flatten_preserves_grains() -> None:
    report, drugs, reactions, bridges = flatten_adverse_event_report(_synthetic_envelope())
    assert report["safetyreportid"] == "SYN-001"
    assert report["receivedate"] == "2024-01-15"
    assert report["synthetic"] is True
    assert len(drugs) == 1
    assert len(reactions) == 1
    assert len(bridges) == 1
    assert bridges[0]["medicinalproduct"] == "SYNTHETICILLIN"


def test_normalize_medicine_name() -> None:
    assert normalize_medicine_name("  Acetaminophen  ") == "acetaminophen"
    assert normalize_ndc("0001-0001") == "00010001"
