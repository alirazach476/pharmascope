#!/usr/bin/env python
"""Run reproducible analytical summaries against the DuckDB warehouse."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.config.settings import get_settings  # noqa: E402
from pharmascope.warehouse.connection import DuckDBWarehouse  # noqa: E402
from pharmascope.warehouse import queries  # noqa: E402


def main() -> int:
    setup_logging()
    settings = get_settings()
    out_dir = settings.project_root / "reports" / "statistical"
    out_dir.mkdir(parents=True, exist_ok=True)

    with DuckDBWarehouse(settings) as wh:
        tables = wh.query_df("SHOW TABLES")["name"].tolist()
        summary: dict = {"tables": tables, "analyses": {}}

        if "fact_adverse_event_reports" in tables:
            trends = queries.adverse_event_trends_by_month(wh)
            top_drugs = queries.top_reported_medicinal_products(wh, limit=15)
            top_rxn = queries.top_reported_reactions(wh, limit=15)
            summary["analyses"]["ae_trends"] = trends.to_dict(orient="records")
            summary["analyses"]["top_reported_products"] = top_drugs.to_dict(orient="records")
            summary["analyses"]["top_reported_reactions"] = top_rxn.to_dict(orient="records")
            trends.to_csv(out_dir / "ae_trends_by_month.csv", index=False)
            top_drugs.to_csv(out_dir / "top_reported_products.csv", index=False)
            top_rxn.to_csv(out_dir / "top_reported_reactions.csv", index=False)

        if "fact_recalls" in tables:
            recall_trends = queries.recall_trends_by_month(wh)
            summary["analyses"]["recall_trends"] = recall_trends.to_dict(orient="records")
            recall_trends.to_csv(out_dir / "recall_trends_by_month.csv", index=False)

        summary["disclaimer"] = (
            "Counts are reported cases from spontaneous/public sources. "
            "They do not prove causation or estimate incidence."
        )

    out_path = out_dir / "analytics_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
