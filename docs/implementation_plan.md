# PharmaScope Implementation Plan

**Status date:** 2026-11-02  
**Approach:** Incremental milestones with a verified runnable state after each stage.

## Milestone 0 — Repository inspection

| Item | Result |
|------|--------|
| Existing files | Empty workspace |
| Python | 3.12.10 available |
| Disk | ~94 GB free on `C:` |
| Git | Not initialized |

## Milestone 1 — Project foundation (Phase 1)

**Deliverables**
- `pyproject.toml` with core + optional `dev` dependencies
- Validated `Settings` via pydantic-settings
- Logging configuration
- `.env.example`, `.gitignore`, `Makefile`
- Package import + unit tests
- Architecture + data source documentation

**Verification**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest -q
```

## Milestone 2 — OpenFDA vertical slice (Phases 2–3)

**Deliverables**
- Source registry (`configs/sources.yaml`)
- Clients: events, NDC, recalls (bounded samples by default)
- Manifests, checkpoints, retry/pagination
- Bronze → silver → gold promotion for adverse events
- DuckDB load + analytical queries

**Verification**
```powershell
python scripts/download_data.py --source openfda_events --limit 200
python scripts/run_transformations.py --source openfda_events
python scripts/run_analytics.py
pytest -q
```

## Milestone 3 — Data quality + warehouse queries (Phases 5–6)

**Deliverables**
- Severity-classified DQ framework + reports
- Gold tables: reports, drugs, reactions, drug-event bridge, recalls, NDC
- Documented grains (no mega-table double counting)

## Milestone 4 — Statistics + safety signals (Phases 7–8)

**Deliverables**
- Wilson CIs, Welch/MW/chi-square/Fisher helpers
- BH multiple-testing correction
- Exploratory ROR with continuity correction + disclaimers

## Milestone 5 — API + dashboard (Phases 10–11)

**Deliverables**
- FastAPI health/sources/analytics/medicines/reports
- Streamlit pages: overview, explorer, safety, recalls, DQ, pipeline

## Milestone 6 — Hardening (completed this session)

- Incremental gold upsert on business keys (idempotent reruns)
- EDA / regression / time-series / sensitivity modules
- Anomaly detection helpers + matching evaluation metrics
- Market + statistical workbench dashboard pages
- Benchmark harness executed on authentic gold sample

## Milestone 7 — Remaining sources & ML (later)

- DailyMed / CMS after schema verification
- Utilization forecasting only with real utilization series
- Price anomaly detection only with comparable price data
- Larger-scale benchmarks / optional dbt

## Risks

| Risk | Mitigation |
|------|------------|
| OpenFDA rate limits / network | Bounded limits; fixtures for offline tests; optional API key |
| Skip cap 25,000 | Document; use bulk downloads for large extracts |
| Misinterpretation of FAERS | Disclaimers in API, dashboard, docs, signal outputs |
| Synthetic contamination | `synthetic` flag + gold write guard |

## Acceptance tracking

See `docs/project_status.md` for checklist progress (verified vs. planned).
