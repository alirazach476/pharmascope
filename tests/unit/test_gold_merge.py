import pandas as pd

from pharmascope.processing.gold_merge import merge_gold_frames


def test_merge_inserts_and_replaces() -> None:
    existing = pd.DataFrame(
        {
            "safetyreportid": ["A", "B"],
            "serious": ["1", "2"],
            "batch_id": ["old", "old"],
        }
    )
    incoming = pd.DataFrame(
        {
            "safetyreportid": ["B", "C"],
            "serious": ["9", "1"],
            "batch_id": ["new", "new"],
        }
    )
    merged, result = merge_gold_frames(
        existing, incoming, keys=["safetyreportid"], table_name="fact_adverse_event_reports"
    )
    assert result.merged_rows == 3
    assert result.rows_inserted == 1
    assert result.rows_updated_or_replaced == 1
    b = merged.loc[merged["safetyreportid"] == "B"].iloc[0]
    assert b["serious"] == "9"
    assert b["batch_id"] == "new"


def test_rerun_same_keys_no_growth() -> None:
    df = pd.DataFrame({"recall_number": ["R1", "R2"], "classification": ["Class I", "Class II"]})
    merged1, _ = merge_gold_frames(None, df, keys=["recall_number"], table_name="fact_recalls")
    merged2, result = merge_gold_frames(
        merged1, df, keys=["recall_number"], table_name="fact_recalls"
    )
    assert len(merged2) == 2
    assert result.rows_inserted == 0
    assert result.rows_updated_or_replaced == 2
