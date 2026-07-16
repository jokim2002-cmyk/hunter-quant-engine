# HQE Multi-Strategy Phase 3A — Registered Backtest Integration

## Scope

Phase 3A routes reviewed registered strategies through HQE's existing
`BacktestPipeline` without editing or replacing the pipeline, engine, trade
planner, risk manager, reports, or product paper runtime.

The result is additive:

- the original `BacktestResult` remains unchanged;
- immutable strategy identity and parameter metadata are attached separately;
- an optional JSON metadata sidecar can be written next to existing reports.

## Registered strategies in this phase

1. `hqe_current_smc_compatibility@1.0.0`
   - preserves the verified current file-based paper decision payload;
   - remains forward-compatibility-only in this phase;
   - is deliberately rejected by the historical backtest adapter because it
     does not implement `generate(StrategyContext)`.

2. `hqe_historical_smc_backtest@1.0.0`
   - wraps the existing `SMCStrategy`;
   - supports existing strict, balanced, and relaxed modes;
   - is routed through the unchanged historical `BacktestPipeline`.

The two manifests are intentionally separate. This phase does not falsely
claim that the historical SMC engine and the current paper candidate are the
same implementation.

## Metadata recorded

- strategy ID and version
- implementation key
- manifest fingerprint
- validated parameter snapshot and hash
- execution mode
- symbol and timeframe
- data identity
- optional data start and end

## Protected boundaries

This phase does not edit or connect to:

- canonical product paper runtime
- forward intraday supervisor
- current SMC live-direction helper
- product UI
- licensing or Machine ID
- Module 131 state, ledger, report, or recovery files

## Next Phase 3 milestone

Build the normalized recorded-data evaluation surface required to run the
current SMC compatibility implementation over backtest/replay inputs without
changing the canonical paper lifecycle.
