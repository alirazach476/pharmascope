#!/usr/bin/env python
"""Generate a clearly labeled synthetic medicine catalog for scale demos.

IMPORTANT: synthetic rows are labeled synthetic=true / synthetic_scale_demo.
Authentic OpenFDA NDC seed rows remain synthetic=false.

Usage::

    python scripts/generate_synthetic_medicines.py --target 50000000
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402

from pharmascope.config.logging_config import setup_logging  # noqa: E402
from pharmascope.config.settings import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=50_000_000)
    parser.add_argument("--skip-parquet", action="store_true")
    args = parser.parse_args()
    setup_logging()
    settings = get_settings()

    out_dir = settings.resolve_data_root() / "synthetic_scale"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "medicines_scale.duckdb"
    parquet_path = out_dir / "medicines_catalog.parquet"
    meta_path = out_dir / "GENERATED_README.json"

    # Recreate DB file cleanly
    for p in (db_path, Path(str(db_path) + ".wal")):
        if p.exists():
            p.unlink()

    authentic_parquet = settings.layer_path("gold") / "dim_medicine_ndc.parquet"
    con = duckdb.connect(str(db_path))
    con.execute("PRAGMA threads=4")

    if authentic_parquet.exists():
        con.execute(
            f"""
            CREATE OR REPLACE TABLE authentic_seed AS
            SELECT
              CAST(product_ndc AS VARCHAR) AS medicine_id,
              CAST(brand_name AS VARCHAR) AS brand_name,
              CAST(generic_name AS VARCHAR) AS generic_name,
              CAST(labeler_name AS VARCHAR) AS manufacturer_name,
              CAST(dosage_form AS VARCHAR) AS dosage_form,
              CAST(route AS VARCHAR) AS route,
              CAST(active_ingredient_names_raw AS VARCHAR) AS active_ingredient,
              CAST(NULL AS VARCHAR) AS therapeutic_class,
              CAST(product_type AS VARCHAR) AS product_type,
              CAST(NULL AS INTEGER) AS strength_mg,
              CAST(NULL AS VARCHAR) AS market_region,
              CAST(NULL AS INTEGER) AS launch_year,
              FALSE AS synthetic,
              'authentic_openfda_ndc' AS data_class,
              'openfda_ndc' AS source_system
            FROM read_parquet('{authentic_parquet.as_posix()}')
            WHERE COALESCE(synthetic, FALSE) = FALSE
            """
        )
    else:
        con.execute(
            """
            CREATE OR REPLACE TABLE authentic_seed AS
            SELECT * FROM (
              SELECT
                NULL::VARCHAR AS medicine_id, NULL::VARCHAR AS brand_name,
                NULL::VARCHAR AS generic_name, NULL::VARCHAR AS manufacturer_name,
                NULL::VARCHAR AS dosage_form, NULL::VARCHAR AS route,
                NULL::VARCHAR AS active_ingredient, NULL::VARCHAR AS therapeutic_class,
                NULL::VARCHAR AS product_type, NULL::INTEGER AS strength_mg,
                NULL::VARCHAR AS market_region, NULL::INTEGER AS launch_year,
                FALSE AS synthetic, 'authentic_openfda_ndc' AS data_class,
                'openfda_ndc' AS source_system
              WHERE 1=0
            )
            """
        )

    authentic_count = int(con.execute("SELECT COUNT(*) FROM authentic_seed").fetchone()[0])
    synthetic_needed = max(args.target - authentic_count, 0)
    print(
        f"Authentic seed: {authentic_count:,}; synthetic: {synthetic_needed:,}; "
        f"target: {args.target:,}"
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE synthetic_fill AS
        SELECT
          'SYN-' || lpad(CAST(i AS VARCHAR), 10, '0') AS medicine_id,
          'SynBrand-' || CAST((i % 500000) AS VARCHAR) AS brand_name,
          upper(
            ['acetaminophen','ibuprofen','metformin','atorvastatin','amlodipine',
             'lisinopril','omeprazole','levothyroxine','losartan','sertraline',
             'gabapentin','amoxicillin','prednisone','albuterol','insulin glargine',
             'rosuvastatin','clopidogrel','pantoprazole','montelukast','tramadol']
            [1 + (i % 20)]
          ) || ' ' || CAST((25 + (i % 40) * 25) AS VARCHAR) || ' MG' AS generic_name,
          'Synthetic Pharma ' || CAST((i % 8000) AS VARCHAR) AS manufacturer_name,
          ['Tablet','Capsule','Injection','Solution','Suspension',
           'Cream','Ointment','Inhaler','Patch','Drops'][1 + (i % 10)] AS dosage_form,
          ['ORAL','INTRAVENOUS','TOPICAL','INHALATION','OPHTHALMIC',
           'SUBCUTANEOUS','TRANSDERMAL'][1 + (i % 7)] AS route,
          ['acetaminophen','ibuprofen','metformin','atorvastatin','amlodipine',
           'lisinopril','omeprazole','levothyroxine','losartan','sertraline',
           'gabapentin','amoxicillin','prednisone','albuterol','insulin glargine',
           'rosuvastatin','clopidogrel','pantoprazole','montelukast','tramadol']
           [1 + (i % 20)] AS active_ingredient,
          ['Cardiovascular','Anti-infective','CNS','Oncology','Endocrine',
           'Respiratory','Gastrointestinal','Analgesic','Dermatology','Vaccine-related']
           [1 + (i % 10)] AS therapeutic_class,
          'HUMAN PRESCRIPTION SYNTHETIC' AS product_type,
          CAST((25 + (i % 40) * 25) AS INTEGER) AS strength_mg,
          ['North America','Europe','Asia-Pacific','Latin America','Middle East','Africa']
           [1 + (i % 6)] AS market_region,
          CAST(1990 + (i % 36) AS INTEGER) AS launch_year,
          TRUE AS synthetic,
          'synthetic_scale_demo' AS data_class,
          'synthetic_generator' AS source_system
        FROM range({synthetic_needed}) t(i)
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE medicines_catalog AS
        SELECT * FROM authentic_seed
        UNION ALL BY NAME
        SELECT * FROM synthetic_fill
        """
    )
    # Drop bulky intermediates
    con.execute("DROP TABLE IF EXISTS synthetic_fill")
    con.execute("DROP TABLE IF EXISTS authentic_seed")

    total = int(con.execute("SELECT COUNT(*) FROM medicines_catalog").fetchone()[0])
    syn_total = int(
        con.execute("SELECT COUNT(*) FROM medicines_catalog WHERE synthetic").fetchone()[0]
    )
    auth_total = total - syn_total
    print(f"Catalog ready: {total:,} rows. Building aggregates...")

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
        SELECT
          CASE WHEN synthetic THEN 'synthetic_scale_demo' ELSE 'authentic_openfda_ndc' END AS origin,
          COUNT(*) AS n
        FROM medicines_catalog GROUP BY 1
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

    if not args.skip_parquet:
        print(f"Writing parquet to {parquet_path} ...")
        con.execute(
            f"COPY medicines_catalog TO '{parquet_path.as_posix()}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )

    meta = {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": args.target,
        "total_medicines": total,
        "authentic_count": auth_total,
        "synthetic_count": syn_total,
        "duckdb_path": str(db_path),
        "parquet_path": str(parquet_path),
        "disclaimer": (
            "Most rows are SYNTHETIC scale-demo records (data_class=synthetic_scale_demo). "
            "Authentic OpenFDA NDC seed rows are labeled synthetic=false."
        ),
        "real_world_note": (
            "No free public finished-medicine catalog contains tens of millions of products. "
            "This catalog uses authentic NDC seed + synthetic fill for scale UI demos."
        ),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
