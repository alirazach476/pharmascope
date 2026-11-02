import pandas as pd

from pharmascope.validation.data_quality import DataQualityFramework
from pharmascope.validation.schemas import ADVERSE_EVENT_REPORT_REQUIRED
from pharmascope.validation.validation_results import Severity


def test_required_columns_and_uniqueness() -> None:
    df = pd.DataFrame(
        {
            "safetyreportid": ["1", "2"],
            "receivedate": ["2024-01-01", "2024-01-02"],
            "source_system": ["openfda_events", "openfda_events"],
            "batch_id": ["b", "b"],
            "ingested_at": ["t", "t"],
        }
    )
    dq = DataQualityFramework("test", "synthetic")
    r1 = dq.check_required_columns(df, ADVERSE_EVENT_REPORT_REQUIRED)
    r2 = dq.check_unique_keys(df, ["safetyreportid", "batch_id"])
    assert r1.passed and r2.passed
    report = dq.build_report()
    assert not report.has_critical_failures


def test_critical_missing_columns() -> None:
    df = pd.DataFrame({"safetyreportid": ["1"]})
    dq = DataQualityFramework("test", "synthetic")
    r = dq.check_required_columns(df, ADVERSE_EVENT_REPORT_REQUIRED, severity=Severity.CRITICAL)
    assert not r.passed
    assert dq.build_report().has_critical_failures
