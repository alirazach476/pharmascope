# PharmaScope Project Status

Last updated: 2026-11-02 (continuation session)

## Verified

| Area | Status | Evidence |
|------|--------|----------|
| Project foundation | Done | editable install |
| OpenFDA events/NDC/recalls samples | Done | authentic API extracts |
| Bronze/silver/gold + DQ | Done | parquet + quality reports |
| **Incremental gold upsert** | **Done** | identical rerun: inserted=0, rows unchanged |
| DuckDB warehouse | Done | 6 gold tables |
| Statistics (CI, tests, ROR, OLS, TS, sensitivity) | Done | unit tests |
| Entity matching evaluation (labeled synthetic pairs) | Done | precision/recall/F1 measured in tests |
| ML anomaly helpers + evaluation metrics | Done | unit tests |
| FastAPI | Done | endpoints against warehouse |
| Streamlit (8 pages) | Done | includes market + statistical workbench |
| **Baseline benchmarks** | **Done** | `reports/benchmarks/benchmark_latest.json` |
| Automated tests | Done | **37 passed** |
| DailyMed / CMS ingestion | Not started | disabled pending schema verification |
| Utilization forecasting models | Guarded | explicit NotConfigured |

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Installs with documented instructions | Verified |
| ≥1 official dataset ingested | Verified |
| Raw + manifests preserved | Verified |
| Silver validated | Verified |
| Warehouse model tested | Verified |
| DQ reports | Verified |
| Medicine matching limitations + eval | Verified (synthetic labeled set) |
| ≥3 statistical analyses | Verified |
| Dashboard uses real data | Verified (code + warehouse) |
| API works | Verified |
| Automated tests | Verified (37) |
| Reruns do not silently duplicate | **Verified** (gold business-key upsert) |
| Baseline benchmark executed | **Verified** |
| README matches implementation | Verified |
| No fabricated observations | Verified |

## Commands (continuation)

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
python scripts/run_benchmarks.py
python scripts/run_transformations.py --source openfda_events   # idempotent upsert
streamlit run src/pharmascope/dashboard/app.py
uvicorn pharmascope.api.main:app --reload --port 8000
```

## Remaining optional backlog

1. DailyMed / CMS after official schema inspection  
2. Larger bounded extracts + partition pruning benchmarks  
3. dbt project when SQL-first modeling is required  
4. Auth for API if exposing beyond localhost  
