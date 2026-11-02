# Data Dictionary (initial gold tables)

## fact_adverse_event_reports

| Column | Description |
|--------|-------------|
| safetyreportid | OpenFDA safety report identifier |
| receivedate | ISO date parsed from YYYYMMDD when valid |
| serious | Seriousness flag from source |
| patient_sex / patient_age | Patient attributes when present |
| source_system | e.g. openfda_events |
| batch_id | Extraction batch |
| synthetic | Must be false in production gold |

## fact_reported_drug_events

Bridge table for exploratory association analysis. **Do not** sum rows as
independent incident counts without understanding the combinatorial grain.

## fact_recalls

Recall number, classification (Class I/II/III), dates, firm, reason, status as
provided by OpenFDA enforcement endpoint.

## dim_medicine_ndc

NDC product attributes from the NDC Directory; brand/generic/labeler/dosage form.
