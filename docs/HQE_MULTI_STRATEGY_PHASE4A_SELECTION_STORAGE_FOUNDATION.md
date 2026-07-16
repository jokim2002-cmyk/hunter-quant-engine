# HQE Multi-Strategy Phase 4A — Disabled Selection and Storage Foundation

## Scope

Phase 4A introduces deterministic strategy-selection evidence and namespaced
state/ledger paths. It remains disconnected from the canonical product paper
runtime.

## Safety behavior

- A selection can be created only from an executable reviewed registration.
- Every selection is permanently marked `DISABLED` and `runtime_connected=false`.
- Strategy switching is blocked when the runtime is running, the position is
  `OPEN` or `HELD`, current state identity mismatches the selection, or legacy
  migration is incomplete.
- The offline store refuses construction with runtime connectivity enabled.
- State and ledger identities must match the selected strategy, version,
  manifest, parameter snapshot, and selection hash.
- Ledger event IDs are append-only and duplicates are rejected.

## Namespace

Artifacts are planned under:

```text
<root>/strategies/<strategy_id>/<strategy_version>/<parameters_hash>/
  selection.json
  state.json
  ledger.csv
  report.md
  reason_log.csv
  recovery.json
  migration.json
```

Phase 4A tests write only to temporary test directories. The installer does not
create runtime selection/state/ledger files and does not touch Module 131.

## Deferred

- legacy state/ledger migration execution
- canonical runtime selection cutover
- UI selection controls
- per-strategy restart recovery wiring
- commit and push
