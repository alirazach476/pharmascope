# SQL marts

Local analytical serving uses DuckDB tables created from gold Parquet
(`GoldRepository.load_gold_into_duckdb`). Optional dbt models can be added under
`src/pharmascope/transformations/dbt_project/` when SQL-first modeling is required.

Current gold tables:

- `fact_adverse_event_reports`
- `dim_reported_drugs`
- `dim_reported_reactions`
- `fact_reported_drug_events`
- `fact_recalls`
- `dim_medicine_ndc`
