"""Access layer for the synthetic-scale medicines catalog."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import duckdb
import pandas as pd

from pharmascope.config.settings import Settings, get_settings


class ScaleCatalogNotReadyError(RuntimeError):
    pass


BREAKDOWNS = {
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

# Compact indication labels for catalog UI (class + common actives).
CLASS_USES: dict[str, str] = {
    "Cardiovascular": "Hypertension, cholesterol, heart disease",
    "Anti-infective": "Bacterial / viral infections",
    "CNS": "Depression, seizures, neuropathic pain",
    "Oncology": "Cancer supportive & antineoplastic care",
    "Endocrine": "Diabetes, thyroid, hormonal disorders",
    "Respiratory": "Asthma, COPD, allergy symptoms",
    "Gastrointestinal": "Acid reflux, ulcers, GI symptoms",
    "Analgesic": "Pain and inflammation relief",
    "Dermatology": "Skin inflammation, topical infections",
    "Vaccine-related": "Immunization & preventive care",
}

# Regional / brand synonyms → catalog ingredient or brand tokens.
NAME_ALIASES: dict[str, list[str]] = {
    "panadol": ["acetaminophen", "paracetamol", "panadol"],
    "paracetamol": ["acetaminophen", "paracetamol", "panadol"],
    "acetaminophen": ["acetaminophen", "paracetamol", "panadol", "tylenol"],
    "tylenol": ["acetaminophen", "paracetamol", "tylenol"],
    "calpol": ["acetaminophen", "paracetamol", "calpol"],
}

INGREDIENT_USES: dict[str, str] = {
    "acetaminophen": "Pain, fever (paracetamol / Panadol)",
    "paracetamol": "Pain, fever (paracetamol / Panadol)",
    "ibuprofen": "Pain, inflammation, fever",
    "metformin": "Type 2 diabetes",
    "atorvastatin": "High cholesterol",
    "amlodipine": "Hypertension, angina",
    "lisinopril": "Hypertension, heart failure",
    "omeprazole": "GERD, ulcers",
    "levothyroxine": "Hypothyroidism",
    "losartan": "Hypertension",
    "sertraline": "Depression, anxiety",
    "gabapentin": "Neuropathic pain, seizures",
    "amoxicillin": "Bacterial infections",
    "prednisone": "Inflammation, autoimmune flares",
    "albuterol": "Asthma, bronchospasm",
    "insulin glargine": "Diabetes (basal insulin)",
    "rosuvastatin": "High cholesterol",
    "clopidogrel": "Antiplatelet / ACS prevention",
    "pantoprazole": "GERD, ulcers",
    "montelukast": "Asthma, allergic rhinitis",
    "tramadol": "Moderate to severe pain",
    "alcohol": "Antiseptic / topical use",
    "zinc oxide": "Skin protection, diaper rash",
    "salicylic acid": "Acne, keratolytic use",
    "menthol": "Topical analgesic / cooling",
    "sodium fluoride": "Dental caries prevention",
    "lidocaine": "Local anesthesia, pain",
}


def resolve_uses(
    therapeutic_class: Any,
    active_ingredient: Any,
    indication: Any = None,
) -> str:
    if indication is not None and str(indication).strip():
        return str(indication).strip()
    ing = str(active_ingredient or "").strip().lower()
    if ing in INGREDIENT_USES:
        return INGREDIENT_USES[ing]
    for key, text in INGREDIENT_USES.items():
        if key in ing or ing in key:
            return text
    cls = str(therapeutic_class or "").strip()
    if cls in CLASS_USES:
        return CLASS_USES[cls]
    if ing:
        return f"Supports therapy involving {ing}"
    return "General pharmaceutical use"


def scale_paths(settings: Settings | None = None) -> dict[str, Path]:
    settings = settings or get_settings()
    root = settings.resolve_data_root() / "synthetic_scale"
    return {
        "root": root,
        "duckdb": root / "medicines_scale.duckdb",
        "parquet": root / "medicines_catalog.parquet",
        "meta": root / "GENERATED_README.json",
    }


@contextmanager
def _connect_ro() -> Iterator[duckdb.DuckDBPyConnection]:
    paths = scale_paths()
    if not paths["duckdb"].exists():
        raise ScaleCatalogNotReadyError(
            "Scale catalog not generated. Run: "
            "python scripts/generate_synthetic_medicines.py --target 50000000"
        )
    con = duckdb.connect(str(paths["duckdb"]), read_only=True)
    try:
        yield con
    finally:
        con.close()


def catalog_ready() -> bool:
    return scale_paths()["duckdb"].exists()


def _clean_stats_row(row: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for k, v in row.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, (int, float)) or hasattr(v, "item"):
            cleaned[k] = int(v)
        else:
            cleaned[k] = v
    return cleaned


def get_stats() -> dict[str, Any]:
    with _connect_ro() as con:
        row = con.execute("SELECT * FROM medicines_stats").fetchdf().iloc[0].to_dict()
    meta_path = scale_paths()["meta"]
    disclaimer = None
    if meta_path.exists():
        import json

        disclaimer = json.loads(meta_path.read_text(encoding="utf-8")).get("disclaimer")
    return {
        **_clean_stats_row(row),
        "disclaimer": disclaimer,
        "data_classes": ["authentic_openfda_ndc", "synthetic_scale_demo"],
    }


def breakdown(table: str) -> pd.DataFrame:
    if table not in BREAKDOWNS:
        raise ValueError(f"Unknown breakdown '{table}'. Allowed: {sorted(BREAKDOWNS)}")
    with _connect_ro() as con:
        return con.execute(f"SELECT * FROM {BREAKDOWNS[table]}").fetchdf()


def dashboard_bundle() -> dict[str, Any]:
    """Single payload of pre-aggregated chart series for the React overview."""
    with _connect_ro() as con:
        stats = _clean_stats_row(
            con.execute("SELECT * FROM medicines_stats").fetchdf().iloc[0].to_dict()
        )
        payload = {
            "stats": stats,
            "by_form": con.execute("SELECT * FROM medicines_by_form").fetchdf().to_dict(
                orient="records"
            ),
            "by_class": con.execute("SELECT * FROM medicines_by_class").fetchdf().to_dict(
                orient="records"
            ),
            "by_route": con.execute("SELECT * FROM medicines_by_route").fetchdf().to_dict(
                orient="records"
            ),
            "by_region": con.execute("SELECT * FROM medicines_by_region").fetchdf().to_dict(
                orient="records"
            ),
            "by_year": con.execute("SELECT * FROM medicines_by_year").fetchdf().to_dict(
                orient="records"
            ),
            "by_strength": con.execute(
                "SELECT * FROM medicines_by_strength"
            ).fetchdf().to_dict(orient="records"),
            "by_ingredient": con.execute(
                "SELECT * FROM medicines_by_ingredient"
            ).fetchdf().to_dict(orient="records"),
            "top_manufacturers": con.execute(
                "SELECT * FROM medicines_top_manufacturers"
            ).fetchdf().to_dict(orient="records"),
            "authenticity": con.execute(
                "SELECT * FROM medicines_authenticity"
            ).fetchdf().to_dict(orient="records"),
            "form_route": con.execute(
                "SELECT * FROM medicines_form_route"
            ).fetchdf().to_dict(orient="records"),
            "class_form": con.execute(
                "SELECT * FROM medicines_class_form"
            ).fetchdf().to_dict(orient="records"),
            "by_source": (
                con.execute("SELECT * FROM medicines_by_source").fetchdf().to_dict(
                    orient="records"
                )
                if "medicines_by_source"
                in {
                    r[0]
                    for r in con.execute(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema='main'"
                    ).fetchall()
                }
                else []
            ),
        }
    meta_path = scale_paths()["meta"]
    if meta_path.exists():
        import json

        payload["disclaimer"] = json.loads(meta_path.read_text(encoding="utf-8")).get(
            "disclaimer"
        )
    return payload


def search_medicines(
    *,
    q: str | None = None,
    dosage_form: str | None = None,
    synthetic: bool | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    clauses = ["1=1"]
    params: list[Any] = []
    rank_params: list[Any] = []
    if q:
        raw = q.strip().lower()
        # Regional brand/INN path: Panadol / paracetamol ↔ US acetaminophen naming.
        if "panadol" in raw:
            clauses.append("lower(COALESCE(brand_name,'')) LIKE '%panadol%'")
            rank_params = ["%panadol%", "%panadol%"]
        elif "calpol" in raw:
            clauses.append("lower(COALESCE(brand_name,'')) LIKE '%calpol%'")
            rank_params = ["%calpol%", "%calpol%"]
        elif "tylenol" in raw:
            clauses.append(
                "(lower(COALESCE(brand_name,'')) LIKE '%tylenol%' "
                "OR lower(COALESCE(active_ingredient,'')) = 'acetaminophen')"
            )
            rank_params = ["%tylenol%", "%tylenol%"]
        elif "paracetamol" in raw or raw == "acetaminophen":
            clauses.append(
                "(lower(COALESCE(generic_name,'')) LIKE '%paracetamol%' "
                "OR lower(COALESCE(generic_name,'')) LIKE '%acetaminophen%' "
                "OR lower(COALESCE(active_ingredient,'')) IN ('acetaminophen','paracetamol'))"
            )
            rank_params = [f"%{raw}%", f"%{raw}%"]
        else:
            like = f"%{raw}%"
            clauses.append(
                "(lower(COALESCE(brand_name,'')) LIKE ? OR lower(COALESCE(generic_name,'')) LIKE ? "
                "OR lower(COALESCE(medicine_id,'')) LIKE ? OR lower(COALESCE(active_ingredient,'')) LIKE ? "
                "OR lower(COALESCE(therapeutic_class,'')) LIKE ? "
                "OR lower(COALESCE(indication,'')) LIKE ? "
                "OR lower(COALESCE(manufacturer_name,'')) LIKE ?)"
            )
            params.extend([like, like, like, like, like, like, like])
            matched_ingredients = [
                ing for ing, text in INGREDIENT_USES.items() if raw in text.lower() or raw in ing
            ]
            if matched_ingredients:
                placeholders = ", ".join(["?"] * len(matched_ingredients))
                clauses[-1] = (
                    f"({clauses[-1][1:-1]} OR lower(COALESCE(active_ingredient,'')) IN ({placeholders}))"
                )
                params.extend(matched_ingredients)
            rank_params = [like, like]
    if dosage_form:
        clauses.append("dosage_form = ?")
        params.append(dosage_form)
    if synthetic is not None:
        clauses.append("synthetic = ?")
        params.append(synthetic)
    if source:
        clauses.append("source_system = ?")
        params.append(source)
    where = " AND ".join(clauses)
    order_sql = (
        "CASE WHEN lower(COALESCE(brand_name,'')) LIKE ? "
        "OR lower(COALESCE(generic_name,'')) LIKE ? THEN 0 ELSE 1 END, medicine_id"
        if rank_params
        else "medicine_id"
    )
    with _connect_ro() as con:
        cols = {r[0] for r in con.execute("DESCRIBE medicines_catalog").fetchall()}
        extra_cols = [
            c
            for c in ("indication", "pack_size", "sale_price", "mrp", "source_url")
            if c in cols
        ]
        extra_sql = (", " + ", ".join(extra_cols)) if extra_cols else ""
        # Cap count scan for snappy UI on 50M-scale LIKE filters.
        total = int(
            con.execute(
                f"""
                SELECT COUNT(*) FROM (
                  SELECT 1 FROM medicines_catalog WHERE {where} LIMIT 100001
                ) t
                """,
                params,
            ).fetchone()[0]
        )
        df = con.execute(
            f"""
            SELECT medicine_id, brand_name, generic_name, manufacturer_name, dosage_form,
                   route, active_ingredient, therapeutic_class, product_type,
                   strength_mg, market_region, launch_year, synthetic,
                   data_class, source_system{extra_sql}
            FROM medicines_catalog
            WHERE {where}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            [*rank_params, *params, limit, offset],
        ).fetchdf()
    rows = df.to_dict(orient="records")
    for row in rows:
        row["uses"] = resolve_uses(
            row.get("therapeutic_class"),
            row.get("active_ingredient"),
            row.get("indication"),
        )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": rows,
        "total_capped": total >= 100001,
    }
