# HQE Multi-Strategy Phase 4J — Disabled One-Active Lifecycle Adapter

## Objective

Phase 4J adds a fail-closed compatibility layer for the roadmap's first forward
paper milestone: one selected registered strategy and the canonical
`FLAT -> OPEN -> HELD -> CLOSED` lifecycle.

The adapter is evidence-only. It prepares an immutable integration plan and
projects lifecycle transitions without changing the protected product runtime.

## Added behavior

- exactly one selected strategy is required,
- multiple active selections fail closed,
- strategy selection, manifest, state, recovery, preflight and runtime evidence
  must share the same immutable identity,
- the existing open-position switch guard is reused,
- a switch can be reviewed only while the runtime is stopped, state is migrated
  and the current position is flat,
- canonical lifecycle transitions are projected deterministically,
- open-position symbol and option-side identity cannot mutate across
  `OPEN/HELD`,
- every result contains a deterministic SHA-256 evidence hash.

## Permanent safety boundary

Phase 4J does not:

- activate or select a strategy in the product runtime,
- connect to or control the canonical paper runtime,
- write canonical or namespaced state/ledger files,
- import or execute package source code,
- change Product UI,
- change broker/data behavior,
- enable real orders, broker execution, auto trading or real money,
- change license or Machine ID behavior.

All control and write authorization fields remain `false`.

## Next core path

After Phase 4J evidence passes, the next step is a guarded namespaced lifecycle
write sandbox for the current reviewed SMC strategy. It must remain isolated
from the canonical product runtime until transition, restart-recovery and
operator-evidence gates pass.
