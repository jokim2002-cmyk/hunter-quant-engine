# HQE Multi-Strategy Phase 4F — Runtime Shadow Hook and Operator Evidence View

## Scope

Phase 4F adds an external, read-only observation contract for product/runtime
status and a validated operator evidence view. It remains disconnected from the
canonical HQE paper lifecycle.

The phase does not edit or import-hook:

- `scripts/hqe_product_app_v2.py`
- `scripts/hqe_paper_product_runtime.py`
- `scripts/run_forward_intraday_paper_supervisor.py`
- Module 131 state, ledger, report, summary, or reason-log files
- licensing or Machine ID code

## Stable runtime observation

A runtime observation contains two immutable reads of the same external status
payload. Their canonical SHA-256 values must match. The observation explicitly
forbids runtime control, lifecycle writes, strategy-state writes, trading-ledger
writes, and broker execution.

## Guarded hook

The hook may run only inside an already-running `READY_FLAT` guarded shadow
session. It binds the stable runtime observation hash to the parity journal
record and delegates strategy comparison to the existing offline parity runner.
It cannot start, stop, control, or cut over the product runtime.

## Operator evidence view

The operator view validates the complete append-only journal hash chain and
produces a read-only summary containing:

- session status and evidence hashes
- cycle, match, and mismatch counts
- LONG/SHORT/NEUTRAL counts
- CE_BUY/PE_BUY/NO_TRADE counts
- observed runtime-status counts
- runtime-observation hashes
- explicit zero-write and zero-cutover safety flags

The view does not modify the journal. A rendered Markdown report may be written
only to a separate external evidence directory.

## Deferred

- canonical product/runtime integration
- lifecycle state or ledger writes
- strategy activation
- product UI control
- commit and push
