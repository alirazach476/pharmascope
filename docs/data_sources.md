# Data Sources

All URLs below are official public documentation or APIs. Licensing and terms
must be respected.

## Enabled (initial vertical slice)

### OpenFDA Drug Adverse Event Reports

- Docs: https://open.fda.gov/apis/drug/event/
- API: `https://api.fda.gov/drug/event.json`
- Bulk: https://open.fda.gov/data/downloads/
- Terms: https://open.fda.gov/apis/terms/
- **Limitation:** Spontaneous reports; no causation; reporting bias; OpenFDA API
  `skip` capped at 25,000 (use bulk for larger extracts).

### OpenFDA NDC Directory

- Docs: https://open.fda.gov/apis/drug/ndc/
- API: `https://api.fda.gov/drug/ndc.json`

### OpenFDA Drug Enforcement / Recalls

- Docs: https://open.fda.gov/apis/drug/enforcement/
- API: `https://api.fda.gov/drug/enforcement.json`

## Configured but disabled until verified

### DailyMed

- Labels: https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm
- Enable in `configs/sources.yaml` after download path/schema validation.

### CMS Medicare Part D Prescribers

- Portal: https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers
- Enable only after confirming drug-level fields in the chosen dataset version.

## Optional API key

OpenFDA allows anonymous access with lower rate limits. Optional key:
https://open.fda.gov/apis/authentication/

Set `OPENFDA_API_KEY` in `.env` (never commit secrets).
