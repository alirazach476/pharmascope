"""Ingest medicine_dataset.csv + Pakistan_medicines.csv into the scale catalog.

Copies sources under data/raw/local_datasets/ and merges mapped rows into
medicines_scale.duckdb (idempotent replace of prior CSV batches).
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from pharmascope.config.settings import get_settings

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = {
    "medicine_dataset.csv": ROOT / "medicine_dataset.csv",
    "Pakistan_medicines.csv": ROOT / "Pakistan_medicines.csv",
}


def _parse_strength_mg(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    m = re.search(r"(\d+(?:\.\d)?)", str(value).replace(",", ""))
    if not m:
        return None
    try:
        return int(float(m.group(1)))
    except ValueError:
        return None


def _parse_money(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "").replace("Rs", "").replace("PKR", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        return float(m.group(1)) if m else None


def _rebuild_aggregates(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_stats AS
        SELECT
          COUNT(*) AS total_medicines,
          SUM(CASE WHEN synthetic THEN 1 ELSE 0 END) AS synthetic_count,
          SUM(CASE WHEN NOT synthetic THEN 1 ELSE 0 END) AS authentic_count,
          COUNT(DISTINCT manufacturer_name) AS manufacturers,
          COUNT(DISTINCT dosage_form) AS dosage_forms,
          COUNT(DISTINCT therapeutic_class) AS therapeutic_classes,
          COUNT(DISTINCT active_ingredient) AS ingredients,
          COUNT(DISTINCT market_region) AS regions,
          COUNT(DISTINCT route) AS routes
        FROM medicines_catalog
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_form AS
        SELECT COALESCE(dosage_form,'(unknown)') AS dosage_form, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_class AS
        SELECT COALESCE(therapeutic_class,'(unknown)') AS therapeutic_class, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_route AS
        SELECT COALESCE(route,'(unknown)') AS route, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_top_manufacturers AS
        SELECT COALESCE(manufacturer_name,'(unknown)') AS manufacturer_name, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC LIMIT 30
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_ingredient AS
        SELECT COALESCE(active_ingredient,'(unknown)') AS active_ingredient, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC LIMIT 30
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_region AS
        SELECT COALESCE(market_region,'(unknown)') AS market_region, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_year AS
        SELECT launch_year, COUNT(*) AS n
        FROM medicines_catalog
        WHERE launch_year IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_strength AS
        SELECT
          CASE
            WHEN strength_mg IS NULL THEN '(unknown)'
            WHEN strength_mg < 100 THEN '<100 mg'
            WHEN strength_mg < 250 THEN '100-249 mg'
            WHEN strength_mg < 500 THEN '250-499 mg'
            ELSE '500+ mg'
          END AS strength_bucket,
          COUNT(*) AS n
        FROM medicines_catalog
        GROUP BY 1 ORDER BY n DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_authenticity AS
        SELECT COALESCE(data_class, '(unknown)') AS origin, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_form_route AS
        SELECT
          COALESCE(dosage_form,'(unknown)') AS dosage_form,
          COALESCE(route,'(unknown)') AS route,
          COUNT(*) AS n
        FROM medicines_catalog
        GROUP BY 1, 2
        ORDER BY n DESC
        LIMIT 80
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_class_form AS
        SELECT
          COALESCE(therapeutic_class,'(unknown)') AS therapeutic_class,
          COALESCE(dosage_form,'(unknown)') AS dosage_form,
          COUNT(*) AS n
        FROM medicines_catalog
        GROUP BY 1, 2
        ORDER BY n DESC
        LIMIT 100
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_by_source AS
        SELECT COALESCE(source_system,'(unknown)') AS source_system, COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1 ORDER BY n DESC
        """
    )


def map_medicine_dataset(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, r in df.iterrows():
        name = str(r.get("Name") or "").strip() or f"Unnamed-{i}"
        indication = str(r.get("Indication") or "").strip() or None
        strength = _parse_strength_mg(r.get("Strength"))
        rows.append(
            {
                "medicine_id": f"MDS-{i:08d}",
                "brand_name": name,
                "generic_name": name,
                "manufacturer_name": str(r.get("Manufacturer") or "").strip() or None,
                "dosage_form": str(r.get("Dosage Form") or "").strip() or None,
                "route": None,
                "active_ingredient": name.split()[0] if name else None,
                "therapeutic_class": str(r.get("Category") or "").strip() or None,
                "product_type": str(r.get("Classification") or "").strip() or None,
                "strength_mg": strength,
                "market_region": "Global (medicine_dataset)",
                "launch_year": None,
                "synthetic": True,
                "data_class": "medicine_dataset_csv",
                "source_system": "medicine_dataset.csv",
                "indication": indication,
                "pack_size": None,
                "sale_price": None,
                "mrp": None,
                "source_url": None,
            }
        )
    return pd.DataFrame(rows)


def map_pakistan_medicines(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, r in df.iterrows():
        name = str(r.get("name") or "").strip() or f"Unnamed-{i}"
        rows.append(
            {
                "medicine_id": f"PK-{i:08d}",
                "brand_name": name,
                "generic_name": name,
                "manufacturer_name": str(r.get("company") or "").strip() or None,
                "dosage_form": None,
                "route": None,
                "active_ingredient": name.split()[0] if name else None,
                "therapeutic_class": None,
                "product_type": "Pakistan retail listing",
                "strength_mg": None,
                "market_region": "Pakistan",
                "launch_year": None,
                "synthetic": False,
                "data_class": "pakistan_medicines_csv",
                "source_system": "Pakistan_medicines.csv",
                "indication": None,
                "pack_size": str(r.get("pack_size") or "").strip() or None,
                "sale_price": _parse_money(r.get("sale_price")),
                "mrp": _parse_money(r.get("mrp")),
                "source_url": str(r.get("link") or "").strip() or None,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    settings = get_settings()
    raw_dir = settings.resolve_data_root() / "raw" / "local_datasets"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, src in SOURCE_FILES.items():
        if not src.exists():
            raise FileNotFoundError(f"Missing source CSV at project root: {src}")
        dest = raw_dir / name
        shutil.copy2(src, dest)
        print(f"Copied {src.name} -> {dest}")

    db_path = settings.resolve_data_root() / "synthetic_scale" / "medicines_scale.duckdb"
    if not db_path.exists():
        raise FileNotFoundError(f"Scale catalog missing: {db_path}")

    md = pd.read_csv(raw_dir / "medicine_dataset.csv", low_memory=False)
    pk = pd.read_csv(raw_dir / "Pakistan_medicines.csv", low_memory=False)
    mapped_md = map_medicine_dataset(md)
    mapped_pk = map_pakistan_medicines(pk)
    incoming = pd.concat([mapped_md, mapped_pk], ignore_index=True)

    con = duckdb.connect(str(db_path))
    # Ensure extended columns exist on the live catalog.
    existing = {
        r[0] for r in con.execute("DESCRIBE medicines_catalog").fetchall()
    }
    for col, typ in [
        ("indication", "VARCHAR"),
        ("pack_size", "VARCHAR"),
        ("sale_price", "DOUBLE"),
        ("mrp", "DOUBLE"),
        ("source_url", "VARCHAR"),
    ]:
        if col not in existing:
            con.execute(f"ALTER TABLE medicines_catalog ADD COLUMN {col} {typ}")

    con.execute(
        """
        DELETE FROM medicines_catalog
        WHERE source_system IN ('medicine_dataset.csv', 'Pakistan_medicines.csv')
           OR data_class IN ('medicine_dataset_csv', 'pakistan_medicines_csv')
           OR medicine_id LIKE 'MDS-%'
           OR medicine_id LIKE 'PK-%'
        """
    )
    con.register("incoming_csv", incoming)
    con.execute(
        """
        INSERT INTO medicines_catalog BY NAME
        SELECT
          medicine_id, brand_name, generic_name, manufacturer_name, dosage_form, route,
          active_ingredient, therapeutic_class, product_type, strength_mg, market_region,
          launch_year, synthetic, data_class, source_system,
          indication, pack_size, sale_price, mrp, source_url
        FROM incoming_csv
        """
    )
    _rebuild_aggregates(con)

    stats = con.execute(
        """
        SELECT source_system, COUNT(*) AS n
        FROM medicines_catalog
        GROUP BY 1
        ORDER BY n DESC
        """
    ).fetchdf()
    total = int(con.execute("SELECT COUNT(*) FROM medicines_catalog").fetchone()[0])
    meta_path = db_path.parent / "GENERATED_README.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(
        {
            "local_csvs_ingested_at": datetime.now(UTC).isoformat(),
            "local_csv_files": [
                "medicine_dataset.csv",
                "Pakistan_medicines.csv",
            ],
            "medicine_dataset_rows": int(len(mapped_md)),
            "pakistan_medicines_rows": int(len(mapped_pk)),
            "total_medicines": total,
            "raw_local_datasets_dir": str(raw_dir),
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    con.close()

    print(f"Catalog total now: {total:,}")
    print(stats.to_string(index=False))
    print(
        json.dumps(
            {
                "medicine_dataset_rows": len(mapped_md),
                "pakistan_medicines_rows": len(mapped_pk),
                "raw_dir": str(raw_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
