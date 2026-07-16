# HQE Multi-Strategy Phase 4C — Isolated Flat-State Copy Executor

## Scope

Phase 4C introduces a reviewed executor for one narrow case:

- the legacy Module 131 migration plan is `READY_FLAT`;
- the operator explicitly confirms the runtime is stopped;
- the destination is isolated offline storage;
- selection activation remains `DISABLED`;
- canonical runtime connection and cutover remain prohibited.

## Copy behavior

The executor:

1. re-verifies every legacy source size, timestamp, and SHA-256;
2. refuses OPEN, running, corrupt, inconsistent, unsafe, or missing-data plans;
3. writes into a unique staging directory;
4. copies all available legacy evidence byte-for-byte into `legacy_source/`;
5. writes the disabled selection snapshot;
6. writes a namespaced FLAT state with `migration_complete=true`;
7. converts legacy ledger events into the namespaced append-only schema;
8. writes recovery and migration evidence;
9. re-verifies the legacy source;
10. atomically promotes the staged namespace.

The raw legacy ledger is preserved byte-for-byte because the new additive ledger
does not contain every historical legacy field.

## Hard safety boundaries

Phase 4C does not:

- modify, move, rename, or delete legacy Module 131 files;
- operate on an OPEN or HELD position;
- connect to the canonical product runtime;
- change active strategy selection;
- cut over state or ledger ownership;
- edit Product UI, licensing, Machine ID, BacktestPipeline, or Module 131;
- commit or push.

## Installer validation

The installer runs the executor only against a synthetic legacy fixture under a
new external dry-run workspace. It compares the real Module 131 read-only audit
before and after that synthetic run to prove the canonical runtime folder was
not changed.
