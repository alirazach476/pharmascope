# Model Card — PharmaScope

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| Utilization forecasting | Not configured | Requires CMS/other utilization series; guarded error |
| Reporting-volume anomaly detection | Implemented helpers | Robust z-score + Isolation Forest; review flags only |
| Price anomaly detection | Not configured | Needs comparable official price observations |
| Entity matching evaluation | Measured on synthetic labeled pairs | See tests — not a production accuracy claim |

## Exploratory statistics (not ML models)

| Method | Type | Claim |
|--------|------|-------|
| Reporting Odds Ratio | Disproportionality | Exploratory reporting signal only |
| Wilson CI / Welch / chi-square / Fisher | Classical stats | Observational helpers |
| Naive / seasonal-naive backtest | Forecasting baseline | Chronological validation only |

## Anomaly detection disclaimer

An anomaly flag means an observation **warrants review**. It does **not** prove
fraud, a pricing violation, or a genuine safety event.

## Registry

Optional artifact metadata can be written under
`data/metadata/model_registry/` via `ModelRegistry`. Metrics must come from
actual evaluation runs — never invent accuracy figures.
