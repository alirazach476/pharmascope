# Architecture Decision Records

## ADR-001: DuckDB + Parquet as primary analytical store

**Decision:** Use Parquet for medallion layers and DuckDB for interactive SQL.  
**Rationale:** Local-first, columnar, low ops overhead vs forcing all data into PostgreSQL.  
**Status:** Accepted.

## ADR-002: Bounded OpenFDA API samples by default

**Decision:** Cap extractions with `PHARMASCOPE_DEV_RECORD_LIMIT` unless
`PHARMASCOPE_ALLOW_FULL_DOWNLOAD=true`.  
**Rationale:** Prevent accidental multi-GB / rate-limit incidents.  
**Status:** Accepted.

## ADR-003: Separate drug×event bridge table

**Decision:** Do not create a single denormalized fact that multiplies report counts.  
**Rationale:** One FAERS report may list multiple drugs and reactions.  
**Status:** Accepted.

## ADR-004: Synthetic data isolation

**Decision:** Refuse gold writes that are 100% synthetic; fixtures live under
`data/synthetic_test_fixtures/`.  
**Rationale:** Prevent fabricated observations in analytical outputs.  
**Status:** Accepted.
