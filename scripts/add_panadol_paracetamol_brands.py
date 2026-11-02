"""Rebrand a slice of acetaminophen synthetic rows as Panadol / paracetamol.

OpenFDA (US) catalogs acetaminophen, not the UK/PK INN paracetamol or the
Panadol brand. This keeps the 50M catalog but adds findable regional names.
"""

from __future__ import annotations

import duckdb

from pharmascope.config.settings import get_settings


def main() -> None:
    path = get_settings().resolve_data_root() / "synthetic_scale" / "medicines_scale.duckdb"
    con = duckdb.connect(str(path))
    before = con.execute(
        """
        SELECT COUNT(*) FROM medicines_catalog
        WHERE synthetic AND lower(active_ingredient) = 'acetaminophen'
          AND (lower(brand_name) LIKE '%panadol%' OR lower(generic_name) LIKE '%paracetamol%')
        """
    ).fetchone()[0]
    con.execute(
        """
        UPDATE medicines_catalog
        SET
          brand_name = ['Panadol', 'Panadol Extra', 'Panadol Advance', 'Panadol Night', 'Calpol']
            [1 + (CAST(right(medicine_id, 4) AS INTEGER) % 5)],
          generic_name = 'paracetamol ' || CAST(strength_mg AS VARCHAR) || ' MG',
          manufacturer_name = 'GSK Consumer Healthcare (synthetic label)',
          market_region = CASE
            WHEN market_region IS NULL THEN 'Asia-Pacific'
            ELSE market_region
          END
        WHERE synthetic
          AND lower(active_ingredient) = 'acetaminophen'
          AND CAST(right(medicine_id, 1) AS INTEGER) IN (0, 5)
        """
    )
    after = con.execute(
        """
        SELECT COUNT(*) FROM medicines_catalog
        WHERE synthetic AND (
          lower(brand_name) LIKE '%panadol%'
          OR lower(brand_name) LIKE '%calpol%'
          OR lower(generic_name) LIKE '%paracetamol%'
        )
        """
    ).fetchone()[0]
    sample = con.execute(
        """
        SELECT brand_name, generic_name, active_ingredient, medicine_id
        FROM medicines_catalog
        WHERE lower(brand_name) LIKE '%panadol%'
        LIMIT 5
        """
    ).fetchdf()
    con.close()
    print(f"Previously branded: {before:,}")
    print(f"Now Panadol/paracetamol/Calpol labeled: {after:,}")
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
