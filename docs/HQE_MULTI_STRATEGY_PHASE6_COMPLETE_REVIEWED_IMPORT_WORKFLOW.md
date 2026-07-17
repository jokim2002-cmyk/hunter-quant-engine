# HQE Multi-Strategy Phase 6 — Complete Reviewed Import Workflow

## Objective

Phase 6 joins the existing offline package quarantine, tamper-evident review,
explicit approval, and atomic metadata installation primitives into one
operator-visible Product App workflow.

## Workflow

1. Choose a data-only strategy package directory.
2. Validate the manifest, checksums, file policy, and safety contract.
3. Copy stable bytes to an isolated quarantine namespace.
4. Create a tamper-evident review request and operator evidence.
5. Require the exact phrase `APPROVE REVIEWED METADATA IMPORT`.
6. Allow approval only when the implementation key already maps to a reviewed
   local implementation.
7. Atomically install metadata into the read-only installed catalog.
8. Preserve complete workflow, approval, install, and audit evidence.

## Duplicate and conflict behavior

An identical repeated metadata installation is idempotent. A package with the
same strategy ID and version but different hashes is rejected without changing
the catalog. Packages with unreviewed implementation keys remain quarantined
and cannot be approved.

## Permanent safety boundary

Phase 6 never imports or executes package source code. It does not copy package
payloads into runtime folders, register implementations, select a strategy,
create the Phase 4 human cutover gate, activate the canonical runtime, start or
stop Paper Trading, write lifecycle/state/ledger evidence, place orders, enable
broker execution, enable real money, or enable option selling.

The existing legacy JSON strategy-pack import remains separate for backward
compatibility. The reviewed workflow is the governed multi-strategy import path.

## Next core path

After the Phase 6 checkpoint, continue with the complete Phase 7 parallel,
isolated paper-observation workflow. No imported metadata becomes active merely
because it is installed.
