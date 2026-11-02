# Data Governance

## Classification

| Class | Location | Rules |
|-------|----------|-------|
| Authentic raw | `data/raw/` | Immutable payloads + ingestion envelope |
| Analytical | `data/bronze|silver|gold/` | No silent synthetic mixing |
| Synthetic fixtures | `data/synthetic_test_fixtures/` | Tests only; labeled `synthetic: true` |
| Quarantine | `data/quarantine/` | Rejected / failed validation |
| Secrets | `.env` (gitignored) | Never in source or logs |

## Provenance

Every extraction writes `data/metadata/manifests/manifest_*.json` including
endpoint, parameters, counts, checksum, status, and timestamps.

## Safety language

This platform is an **analytical research tool**, not a validated clinical
decision-support system. Dashboard and API responses include disclaimers.

## Retention

Local development retains raw and analytical files until manually purged.
Do not publish individual-level sensitive attributes; OpenFDA public fields only.
