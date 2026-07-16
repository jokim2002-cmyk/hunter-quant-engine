# HQE Multi-Strategy Phase 2 — Current SMC Compatibility Adapter

## Scope

This phase adds a read-only compatibility adapter around the verified
`scripts/hqe_smc_live_direction.py` implementation.

It does not edit or connect to:

- `scripts/run_forward_intraday_paper_supervisor.py`
- `scripts/hqe_paper_product_runtime.py`
- `scripts/hqe_product_app_v2.py`
- licensing or Machine ID code
- Module 131 state or ledger files

## Compatibility rule

The adapter delegates to the current helper instead of duplicating its logic.
Every evaluation returns:

1. a structured versioned `StrategyDecision`; and
2. a defensive copy of the exact legacy payload.

The structured output keeps canonical strategy direction:

- `LONG -> CE_BUY`
- `SHORT -> PE_BUY`
- `NEUTRAL -> NO_TRADE`

When the current helper requests its historical PE-only fallback, the
structured signal is `NEUTRAL`, `fallback_to_legacy` is true, and the exact
legacy `PE_BUY` compatibility payload remains available. No fallback behavior
is executed by this adapter.

## Parameter safety

The current implementation hardcodes the ER20 threshold at `0.30`. The Phase 2
manifest therefore fixes `er20_min` to exactly `0.30`; unsupported threshold
changes fail validation rather than silently claiming configurability.

## Deferred

- canonical runtime cutover
- backtest routing
- common normalized strategy context
- state and ledger migration
- UI strategy selection
- commit and push
