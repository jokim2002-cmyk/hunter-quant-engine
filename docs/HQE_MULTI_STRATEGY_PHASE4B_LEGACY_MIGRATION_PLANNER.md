# HQE Multi-Strategy Phase 4B — Read-Only Legacy Migration Planner

## Scope

Phase 4B reads the existing `HQE_PAPER_PRODUCT_RUNTIME` Module 131 evidence and
produces a deterministic migration/recovery plan. It does not copy, move,
rename, delete, rewrite, or cut over any legacy or namespaced file.

## Evidence inspected

- `HQE_PAPER_PRODUCT_RUNTIME.json`
- `MODULE_131_POSITION_STATE.json`
- `MODULE_131_PAPER_LEDGER.csv`
- `MODULE_131_SUPERVISOR_SUMMARY.json`
- `MODULE_131_INTRADAY_SUPERVISOR_REPORT.md`
- `MODULE_131_SIGNAL_REASON_LOG.csv`

Each existing file is identified by absolute path, byte size, modification
timestamp, and SHA-256. The planner reads evidence twice and fails if anything
changes during planning.

## Readiness outcomes

- `READY_FLAT`
- `NO_LEGACY_DATA`
- `BLOCKED_RUNTIME_RUNNING`
- `BLOCKED_OPEN_POSITION`
- `BLOCKED_CORRUPT_STATE`
- `BLOCKED_LEDGER_INCONSISTENT`
- `BLOCKED_SAFETY_VIOLATION`

An OPEN legacy position is represented in-memory for restart-recovery parity,
but it is never marked migrated and never moved away from the working runtime.

## Recovery compatibility

The planner can produce a read-only recovery snapshot containing:

- exact selection identity
- migration plan hash
- legacy state and ledger hashes
- namespaced state shape
- OPEN-position details when present
- `migration_complete=false`
- `runtime_connected=false`

## Hard boundary

Phase 4B contains no migration executor. Calling the execution gate always
raises `MigrationExecutionDisabledError`.

The canonical product runtime, Module 131 files, product UI, licensing, Machine
ID, broker safety, and release baseline remain untouched.

## Read-only CLI

`hqe_multi_strategy_legacy_migration_audit.py` prints the deterministic plan and recovery snapshot to stdout. It never writes or executes migration.
