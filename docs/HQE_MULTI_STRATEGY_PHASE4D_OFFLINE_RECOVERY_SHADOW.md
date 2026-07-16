# HQE Multi-Strategy Phase 4D — Offline Recovery and Shadow Parity

## Scope

Phase 4D validates the isolated Phase 4C namespaced copy as restart evidence and
compares the current registered strategy decision against the direct legacy
helper in an offline shadow run.

This phase does not connect to the canonical paper runtime and does not write
strategy state or ledger events.

## Offline restart-recovery reader

The reader accepts only a completed, disabled, `FLAT` namespace. It verifies:

- selection ID, version, manifest fingerprint, parameters, and selection hash;
- state identity, `FLAT` lifecycle, migration completion, and last event ID;
- ledger schema, strategy identity, unique event IDs, and OPEN/CLOSED sequence;
- recovery and migration evidence;
- migration `result_hash`;
- destination artifact hashes;
- archived legacy source hashes;
- stable double-read hashes for every validated artifact.

Any missing, corrupt, runtime-connected, cut-over, non-FLAT, or inconsistent
artifact fails closed.

## Offline shadow parity

The shadow runner requires the validated `READY_FLAT` recovery snapshot. It
materializes temporary compatibility CSV files, then evaluates the same input:

1. directly through `hqe_smc_live_direction.evaluate_from_csv`; and
2. through the registered current-SMC adapter with execution mode
   `FORWARD_PAPER`.

It requires deterministic repeated outputs and exact legacy-payload parity.
It records no state, ledger, report, selection, or runtime changes.

## Deferred

- canonical product-runtime connection
- Module 131 state/ledger cutover
- UI strategy activation
- actual legacy migration
- commit and push
