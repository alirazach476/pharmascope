"""JSON flattening for OpenFDA nested payloads.

Keeps report-level, drug-level, and reaction-level grains separate to avoid
multiplying event counts when one report contains multiple drugs and events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def _parse_openfda_date(value: Any) -> str | None:
    """Parse OpenFDA YYYYMMDD dates to ISO date strings when valid."""
    if value is None or value == "":
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        try:
            return datetime.strptime(text, "%Y%m%d").date().isoformat()
        except ValueError:
            return None
    return text


def flatten_adverse_event_report(
    envelope: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Flatten one raw envelope into report, drugs, reactions, and bridges.

    Returns
    -------
    report_row, drug_rows, reaction_rows, drug_event_rows
    """
    meta = envelope.get("_ingestion") or {}
    payload = envelope.get("payload") or envelope

    safetyreportid = payload.get("safetyreportid")
    report_row = {
        "safetyreportid": safetyreportid,
        "receivedate": _parse_openfda_date(payload.get("receivedate")),
        "receiptdate": _parse_openfda_date(payload.get("receiptdate")),
        "serious": payload.get("serious"),
        "seriousnessdeath": payload.get("seriousnessdeath"),
        "seriousnesshospitalization": payload.get("seriousnesshospitalization"),
        "seriousnesslifethreatening": payload.get("seriousnesslifethreatening"),
        "seriousnessdisabling": payload.get("seriousnessdisabling"),
        "seriousnesscongenitalanomali": payload.get("seriousnesscongenitalanomali"),
        "seriousnessother": payload.get("seriousnessother"),
        "primarysourcecountry": payload.get("primarysourcecountry"),
        "occurcountry": payload.get("occurcountry"),
        "companynumb": payload.get("companynumb"),
        "fulfiliaxind": payload.get("fulfiliaxind"),
        "source_system": meta.get("source", "openfda_events"),
        "batch_id": meta.get("batch_id"),
        "ingested_at": meta.get("ingested_at"),
        "synthetic": bool(meta.get("synthetic", False)),
    }

    patient = payload.get("patient") or {}
    report_row["patient_sex"] = patient.get("patientsex")
    report_row["patient_age"] = patient.get("patientonsetage")
    report_row["patient_age_unit"] = patient.get("patientonsetageunit")

    drugs = patient.get("drug") or []
    reactions = patient.get("reaction") or []

    drug_rows: list[dict[str, Any]] = []
    for idx, drug in enumerate(drugs if isinstance(drugs, list) else []):
        openfda = drug.get("openfda") or {}
        drug_rows.append(
            {
                "safetyreportid": safetyreportid,
                "drug_index": idx,
                "medicinalproduct": drug.get("medicinalproduct"),
                "drugcharacterization": drug.get("drugcharacterization"),
                "drugindication": drug.get("drugindication"),
                "drugdosagetext": drug.get("drugdosagetext"),
                "drugadministrationroute": drug.get("drugadministrationroute"),
                "activesubstance_name": ((drug.get("activesubstance") or {}).get("activesubstancename")),
                "brand_name": _first(openfda.get("brand_name")),
                "generic_name": _first(openfda.get("generic_name")),
                "substance_name": _first(openfda.get("substance_name")),
                "manufacturer_name": _first(openfda.get("manufacturer_name")),
                "product_ndc": _first(openfda.get("product_ndc")),
                "route": _first(openfda.get("route")),
                "source_system": meta.get("source", "openfda_events"),
                "batch_id": meta.get("batch_id"),
                "synthetic": bool(meta.get("synthetic", False)),
            }
        )

    reaction_rows: list[dict[str, Any]] = []
    for idx, reaction in enumerate(reactions if isinstance(reactions, list) else []):
        reaction_rows.append(
            {
                "safetyreportid": safetyreportid,
                "event_index": idx,
                "reaction_pt": reaction.get("reactionmeddrapt"),
                "reaction_outcome": reaction.get("reactionoutcome"),
                "source_system": meta.get("source", "openfda_events"),
                "batch_id": meta.get("batch_id"),
                "synthetic": bool(meta.get("synthetic", False)),
            }
        )

    # Bridge at drug×event grain — explicit combinatorial relationship
    drug_event_rows: list[dict[str, Any]] = []
    for drug in drug_rows:
        for reaction in reaction_rows:
            drug_event_rows.append(
                {
                    "safetyreportid": safetyreportid,
                    "drug_index": drug["drug_index"],
                    "event_index": reaction["event_index"],
                    "medicinalproduct": drug["medicinalproduct"],
                    "drugcharacterization": drug["drugcharacterization"],
                    "reaction_pt": reaction["reaction_pt"],
                    "source_system": meta.get("source", "openfda_events"),
                    "batch_id": meta.get("batch_id"),
                    "synthetic": bool(meta.get("synthetic", False)),
                    "counting_note": (
                        "Pair row for exploratory association analysis; "
                        "do not sum as independent incident counts without care."
                    ),
                }
            )

    return report_row, drug_rows, reaction_rows, drug_event_rows


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def flatten_envelopes_to_frames(
    envelopes: list[dict[str, Any]],
) -> dict[str, pd.DataFrame]:
    """Convert a list of raw envelopes into silver-ready DataFrames."""
    reports: list[dict[str, Any]] = []
    drugs: list[dict[str, Any]] = []
    reactions: list[dict[str, Any]] = []
    bridges: list[dict[str, Any]] = []

    for env in envelopes:
        report, drug_rows, reaction_rows, bridge_rows = flatten_adverse_event_report(env)
        reports.append(report)
        drugs.extend(drug_rows)
        reactions.extend(reaction_rows)
        bridges.extend(bridge_rows)

    return {
        "fact_adverse_event_reports": pd.DataFrame(reports),
        "dim_reported_drugs": pd.DataFrame(drugs),
        "dim_reported_reactions": pd.DataFrame(reactions),
        "fact_reported_drug_events": pd.DataFrame(bridges),
    }


def flatten_recall_record(envelope: dict[str, Any]) -> dict[str, Any]:
    meta = envelope.get("_ingestion") or {}
    payload = envelope.get("payload") or envelope
    return {
        "recall_number": payload.get("recall_number"),
        "classification": payload.get("classification"),
        "status": payload.get("status"),
        "report_date": _parse_openfda_date(payload.get("report_date")),
        "recall_initiation_date": _parse_openfda_date(payload.get("recall_initiation_date")),
        "termination_date": _parse_openfda_date(payload.get("termination_date")),
        "recalling_firm": payload.get("recalling_firm"),
        "city": payload.get("city"),
        "state": payload.get("state"),
        "country": payload.get("country"),
        "product_description": payload.get("product_description"),
        "reason_for_recall": payload.get("reason_for_recall"),
        "product_quantity": payload.get("product_quantity"),
        "code_info": payload.get("code_info"),
        "distribution_pattern": payload.get("distribution_pattern"),
        "voluntary_mandated": payload.get("voluntary_mandated"),
        "initial_firm_notification": payload.get("initial_firm_notification"),
        "event_id": payload.get("event_id"),
        "product_type": payload.get("product_type"),
        "source_system": meta.get("source", "openfda_recalls"),
        "batch_id": meta.get("batch_id"),
        "ingested_at": meta.get("ingested_at"),
        "synthetic": bool(meta.get("synthetic", False)),
    }


def flatten_ndc_record(envelope: dict[str, Any]) -> dict[str, Any]:
    meta = envelope.get("_ingestion") or {}
    payload = envelope.get("payload") or envelope
    active = payload.get("active_ingredients") or []
    ingredient_names = []
    strengths = []
    if isinstance(active, list):
        for item in active:
            if isinstance(item, dict):
                ingredient_names.append(item.get("name"))
                strengths.append(item.get("strength"))
    return {
        "product_ndc": payload.get("product_ndc"),
        "generic_name": payload.get("generic_name"),
        "brand_name": _first(payload.get("brand_name")),
        "labeler_name": payload.get("labeler_name"),
        "dosage_form": payload.get("dosage_form"),
        "route": _first(payload.get("route")),
        "product_type": payload.get("product_type"),
        "marketing_start_date": _parse_openfda_date(payload.get("marketing_start_date")),
        "marketing_category": payload.get("marketing_category"),
        "application_number": payload.get("application_number"),
        "active_ingredient_names_raw": "; ".join(str(x) for x in ingredient_names if x),
        "active_ingredient_strengths_raw": "; ".join(str(x) for x in strengths if x),
        "source_system": meta.get("source", "openfda_ndc"),
        "batch_id": meta.get("batch_id"),
        "ingested_at": meta.get("ingested_at"),
        "synthetic": bool(meta.get("synthetic", False)),
    }
