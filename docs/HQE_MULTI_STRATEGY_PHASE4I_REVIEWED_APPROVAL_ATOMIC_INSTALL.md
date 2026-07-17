# HQE Multi-Strategy Phase 4I — Reviewed Approval and Atomic Metadata Installation

## Objective

Phase 4I adds a reviewed approval workflow and an atomic metadata-only catalog
installation path on top of the Phase 4H quarantine/catalog foundation.

## Scope

This phase adds:

- tamper-evident review requests,
- tamper-evident approval records,
- reviewed implementation-key allowlisting,
- atomic replacement of one metadata catalog file,
- idempotent repeat installation,
- strategy/version collision rejection,
- post-write catalog hash verification,
- an offline synthetic dry-run,
- focused regression tests.

## Permanent safety boundary

Phase 4I does not:

- import or execute package source code,
- copy package payloads into runtime directories,
- register a strategy implementation,
- select or activate a strategy,
- connect to the canonical paper lifecycle,
- change Product UI,
- change broker or market-data behavior,
- enable real orders, broker execution, auto trading or real money,
- modify licensing or Machine ID behavior.

Installed entries are metadata-only and explicitly record all runtime controls as
disabled.

## Atomicity

The installer uses an exclusive lock plus a temporary file, flush, `fsync` and
`os.replace` for the catalog update. Any temporary file is removed during
cleanup. A repeated identical installation is idempotent. A conflicting package
for the same strategy/version is rejected without changing the catalog.

## Next core path

After Phase 4I evidence passes, the next task is a disabled canonical
one-active-strategy lifecycle integration adapter. Activation must remain off
until its compatibility, restart recovery and operator evidence gates pass.
