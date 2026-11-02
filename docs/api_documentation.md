# API Documentation

Interactive OpenAPI: `http://127.0.0.1:8000/docs` after starting uvicorn.

## Endpoints (implemented)

| Method | Path | Behaviour |
|--------|------|-----------|
| GET | `/health` | Liveness + disclaimer |
| GET | `/api/v1/sources` | Source registry from `configs/sources.yaml` |
| GET | `/api/v1/pipeline/runs` | Extraction manifests |
| GET | `/api/v1/data-quality/summary` | Recent DQ reports |
| GET | `/api/v1/medicines` | NDC or reported-drug listing |
| GET | `/api/v1/medicines/{id}` | NDC product by `product_ndc` |
| GET | `/api/v1/analytics/adverse-events/trends` | Monthly distinct reports |
| GET | `/api/v1/analytics/adverse-events/top-reported` | Top medicinal products |
| GET | `/api/v1/analytics/recalls/trends` | Recall trends if loaded |
| GET | `/api/v1/analytics/prices/trends` | Structured `dataset_not_configured` |
| GET | `/api/v1/analytics/utilization/trends` | Structured `dataset_not_configured` |
| GET | `/api/v1/analytics/forecasts` | Structured `dataset_not_configured` |
| GET | `/api/v1/reports/statistical` | Analytics summary JSON if present |

Unavailable datasets return explicit configuration errors — never fabricated series.
