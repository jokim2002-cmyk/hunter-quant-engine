# HQE Live Readiness Preflight

The live-readiness preflight runs the full safe local chain:

1. Paper MVP operator demo
2. Paper evidence aggregate
3. Live-readiness gate
4. Live safety lock
5. Final preflight report

It is not live trading.

It does not enable real money.
It does not enable broker execution.
It does not enable live market data.
It does not enable real orders.
It does not claim profitability.

## Command

Run:

    .\hqe_live_readiness_preflight.bat

The command writes:

    reports\paper_trading\live_readiness_preflight\preflight.json
    reports\paper_trading\live_readiness_preflight\preflight.txt
    reports\paper_trading\live_readiness_preflight\manifest.json

It also refreshes local stage outputs under:

    reports\paper_trading\operator_demo
    reports\paper_trading\evidence_aggregate
    reports\paper_trading\live_readiness
    reports\paper_trading\live_safety_lock

## Meaning of Pass

A pass means:

    the safe local preflight chain passed

A pass does not mean:

- live trading is approved
- real money is enabled
- broker execution is enabled
- live market data is enabled
- real orders are enabled
- the strategy is profitable

## Operator Rule

Run this before any future live-readiness engineering module.

If it fails, stop and fix the blocker before continuing.
