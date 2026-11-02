"""Export catalog aggregates + searchable medicine samples for Vercel static hosting."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from pharmascope.config.settings import get_settings
from pharmascope.warehouse.scale_catalog import resolve_uses

OUT = Path(__file__).resolve().parents[1] / "web" / "public" / "static-api"


def _records(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    return con.execute(sql).fetchdf().to_dict(orient="records")


def _enrich(rows: list[dict]) -> list[dict]:
    for row in rows:
        for k, v in list(row.items()):
            if hasattr(v, "item"):
                row[k] = v.item()
            elif v is None:
                continue
            elif isinstance(v, float) and v != v:  # NaN
                row[k] = None
        row["uses"] = resolve_uses(
            row.get("therapeutic_class"),
            row.get("active_ingredient"),
            row.get("indication"),
        )
    return rows


def main() -> None:
    db = get_settings().resolve_data_root() / "synthetic_scale" / "medicines_scale.duckdb"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "breakdown").mkdir(exist_ok=True)

    con = duckdb.connect(str(db), read_only=True)
    stats = _records(con, "SELECT * FROM medicines_stats")[0]
    for k, v in list(stats.items()):
        if hasattr(v, "item"):
            stats[k] = int(v)

    dashboard = {
        "stats": stats,
        "by_form": _records(con, "SELECT * FROM medicines_by_form"),
        "by_class": _records(con, "SELECT * FROM medicines_by_class"),
        "by_route": _records(con, "SELECT * FROM medicines_by_route"),
        "by_region": _records(con, "SELECT * FROM medicines_by_region"),
        "by_year": _records(con, "SELECT * FROM medicines_by_year"),
        "by_strength": _records(con, "SELECT * FROM medicines_by_strength"),
        "by_ingredient": _records(con, "SELECT * FROM medicines_by_ingredient"),
        "top_manufacturers": _records(con, "SELECT * FROM medicines_top_manufacturers"),
        "authenticity": _records(con, "SELECT * FROM medicines_authenticity"),
        "form_route": _records(con, "SELECT * FROM medicines_form_route"),
        "class_form": _records(con, "SELECT * FROM medicines_class_form"),
        "by_source": _records(con, "SELECT * FROM medicines_by_source"),
        "disclaimer": "Vercel static snapshot — full 50M catalog served via pre-aggregated marts + sample rows.",
    }
    (OUT / "dashboard.json").write_text(json.dumps(dashboard, default=str), encoding="utf-8")
    (OUT / "stats.json").write_text(json.dumps(stats, default=str), encoding="utf-8")
    (OUT / "status.json").write_text(
        json.dumps({"ready": True, "stats": stats, "mode": "static_vercel"}, default=str),
        encoding="utf-8",
    )

    breakdowns = {
        "form": "medicines_by_form",
        "class": "medicines_by_class",
        "route": "medicines_by_route",
        "manufacturer": "medicines_top_manufacturers",
        "ingredient": "medicines_by_ingredient",
        "region": "medicines_by_region",
        "year": "medicines_by_year",
        "strength": "medicines_by_strength",
        "authenticity": "medicines_authenticity",
        "form_route": "medicines_form_route",
        "class_form": "medicines_class_form",
        "source": "medicines_by_source",
    }
    for kind, table in breakdowns.items():
        payload = {"kind": kind, "data": _records(con, f"SELECT * FROM {table}")}
        (OUT / "breakdown" / f"{kind}.json").write_text(
            json.dumps(payload, default=str), encoding="utf-8"
        )

    cols = (
        "medicine_id, brand_name, generic_name, manufacturer_name, dosage_form, route, "
        "active_ingredient, therapeutic_class, product_type, strength_mg, market_region, "
        "launch_year, synthetic, data_class, source_system, indication, pack_size, "
        "sale_price, mrp, source_url"
    )
    # Search pack: full local CSVs + OpenFDA seed + capped Panadol/Calpol brands.
    medicines = _records(
        con,
        f"""
        SELECT {cols} FROM medicines_catalog
        WHERE source_system IN ('Pakistan_medicines.csv', 'medicine_dataset.csv', 'openfda_ndc')
        UNION ALL
        SELECT {cols} FROM (
          SELECT {cols} FROM medicines_catalog
          WHERE lower(COALESCE(brand_name,'')) LIKE '%panadol%'
             OR lower(COALESCE(brand_name,'')) LIKE '%calpol%'
          LIMIT 4000
        )
        """,
    )
    medicines = _enrich(medicines)
    (OUT / "medicines.json").write_text(json.dumps(medicines, default=str), encoding="utf-8")

    # Optional warehouse analytics — empty-safe.
    ae = {"data": []}
    top = {"data": []}
    recalls = {"data": []}
    try:
        meta = get_settings().resolve_data_root() / "metadata" / "pharmascope.duckdb"
        if meta.exists():
            mcon = duckdb.connect(str(meta), read_only=True)
            tables = {r[0] for r in mcon.execute("SHOW TABLES").fetchall()}
            if "fact_adverse_events" in tables or "gold_adverse_events" in tables:
                pass
            mcon.close()
    except Exception:
        pass
    (OUT / "ae_trends.json").write_text(json.dumps(ae), encoding="utf-8")
    (OUT / "top_reported.json").write_text(json.dumps(top), encoding="utf-8")
    (OUT / "recall_trends.json").write_text(json.dumps(recalls), encoding="utf-8")
    (OUT / "health.json").write_text(
        json.dumps({"status": "ok", "version": "0.1.0", "mode": "static_vercel"}),
        encoding="utf-8",
    )
    (OUT / "sources.json").write_text(json.dumps({"sources": dashboard["by_source"]}), encoding="utf-8")
    (OUT / "dq_summary.json").write_text(json.dumps({"reports": [], "count": 0}), encoding="utf-8")
    (OUT / "pipeline_runs.json").write_text(json.dumps({"runs": [], "count": 0}), encoding="utf-8")

    con.close()
    size_mb = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / (1024 * 1024)
    print(f"Exported static API to {OUT} ({size_mb:.1f} MB, medicines={len(medicines):,})")


if __name__ == "__main__":
    main()
