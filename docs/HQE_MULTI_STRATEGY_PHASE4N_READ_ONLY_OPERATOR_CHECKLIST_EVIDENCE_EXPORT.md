# HQE Multi-Strategy Phase 4N — Read-Only Operator Checklist and Evidence Export

Phase 4N converts the Phase 4M disabled cutover-readiness certificate into a
deterministic operator checklist and an isolated metadata-only review bundle.

## Boundary

- The checklist is read-only and has zero activation authority.
- Only `READY_FLAT_DISABLED` evidence may produce a review export.
- Exports are restricted to a path containing
  `HQE_MULTI_STRATEGY_PHASE4N_REVIEW_EXPORT`.
- The export contains certificate, view, checklist, and a tamper-evident
  manifest. It does not copy canonical Module 131 state, ledger, or runtime
  files.
- Canonical runtime, canonical state/ledger, strategy selection, broker
  execution, and real-money controls remain disabled.
- The bundle is for later human review only; it is not a cutover command.

## Fail-closed statuses

The checklist blocks on certificate status, view mismatch, identity mismatch,
incomplete evidence, or any authority flag. Export verification blocks on
manifest tampering, file tampering, missing files, unsafe paths, or identity
collision.
