# Synthetic test fixtures

These files are **synthetic** and exist only for offline unit/integration tests.

They must **never** be mixed into production analytical tables (`data/bronze`,
`data/silver`, `data/gold`) without an explicit `synthetic=true` exclusion path.

Authentic OpenFDA extractions are stored under `data/raw/` with
`_ingestion.synthetic = false`.
