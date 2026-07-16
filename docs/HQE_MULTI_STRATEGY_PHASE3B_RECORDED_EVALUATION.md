# HQE Multi-Strategy Phase 3B — Normalized Recorded Evaluation

## Scope

Phase 3B adds a normalized input surface for the reviewed current-SMC
compatibility adapter. The exact same registered implementation can now be
evaluated as:

- `BACKTEST` decision evaluation,
- `RECORDED_REPLAY`, or
- a future `FORWARD_PAPER` decision evaluation.

The execution mode changes metadata only. It does not select a different
strategy implementation.

## Input contract

`RecordedStrategyInput` holds immutable normalized:

- index OHLCV rows,
- CE/PE option-premium rows,
- ER20,
- symbol and timeframe,
- optional data start and end.

Every input receives a deterministic SHA-256 identity. Row key order does not
change that identity. Missing required fields, non-finite numbers, empty data,
or timeframe mismatch fail closed.

## Compatibility bridge

The verified current strategy still consumes CSV paths. Phase 3B therefore:

1. serializes normalized rows deterministically;
2. creates temporary compatibility CSV files;
3. calls the reviewed current-SMC adapter;
4. deletes the temporary directory automatically;
5. verifies strategy ID, version, and parameter hash parity.

No Module 131 state, ledger, report, runtime, or product UI file is read or
written by this surface.

## Important boundary

`FORWARD_PAPER` is an execution identity supported by the contract. The
canonical paper runtime is **not connected** in this phase.

This phase is decision evaluation, not a P&L simulator and not a product
runtime cutover.

## Next step

Add versioned strategy selection and per-strategy state/ledger planning behind
a disabled integration gate, then prove migration and restart-recovery behavior
before any canonical runtime switch.
