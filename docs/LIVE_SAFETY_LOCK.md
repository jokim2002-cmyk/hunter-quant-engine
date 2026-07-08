# HQE Live Safety Lock

The live safety lock is a disabled-by-default safety scaffold for future
live-readiness engineering.

It is not live trading.

It does not enable real money.
It does not enable broker execution.
It does not enable live market data.
It does not enable real orders.
It does not claim profitability.

## Command

Run:

    .\scripts\paper_trading\hqe_live_safety_lock_check.bat

The command writes:

    reports\paper_trading\live_safety_lock\live_safety_lock.json
    reports\paper_trading\live_safety_lock\live_safety_lock.txt
    reports\paper_trading\live_safety_lock\manifest.json

## Default Safety Policy

The default policy requires:

- real money disabled
- broker execution disabled
- live market data disabled
- real orders disabled
- manual arming required
- max single order quantity set to 0
- max daily order count set to 0

## Meaning of Pass

A pass means:

    the safety lock is closed and dangerous live features are disabled

A pass does not mean:

- live trading is approved
- real money is approved
- broker execution is approved
- the strategy is profitable

## Operator Rule

Do not change safety flags casually.

Any future change from disabled to enabled must be a separate reviewed module
with tests, documentation, explicit operator acknowledgement, and rollback steps.
