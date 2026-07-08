# HQE Live-Readiness Scaffold v0.2 Release Notes

Hunter Quant Engine Live-Readiness Scaffold v0.2 is a safety checkpoint after
Paper MVP v0.1.

This release adds safe local live-readiness engineering scaffolding while
keeping live trading disabled.

## Safety Boundary

This release is not live trading.

It does not enable real money.
It does not enable broker execution.
It does not enable broker submission.
It does not enable live market data.
It does not enable real orders.
It does not claim profitability.

## Release Tag

Release tag name:

    v0.2-live-readiness-scaffold

## Included Modules After Paper MVP v0.1

This checkpoint includes:

- Paper evidence aggregate runner.
- Live-readiness gate scaffold.
- Disabled live safety lock scaffold.
- Full live-readiness preflight.
- Deny-only live execution firewall.
- Firewall integration into the live-readiness preflight.

## Main Operator Commands

Run the full test suite:

    .\scripts\paper_trading\hqe_quick_check.bat

Run the full safe preflight:

    .\scripts\paper_trading\hqe_live_readiness_preflight.bat

Run the deny-only firewall directly:

    .\scripts\paper_trading\hqe_live_execution_firewall_check.bat

Run the disabled safety lock directly:

    .\scripts\paper_trading\hqe_live_safety_lock_check.bat

## Meaning of Pass

A pass means:

    safe local live-readiness scaffolding is working

A pass does not mean:

- live trading is approved
- real money is enabled
- broker execution is enabled
- broker submission is enabled
- live market data is enabled
- real orders are enabled
- the strategy is profitable

## Next Phase

After v0.2, the next phase can add more live-readiness engineering only behind
disabled-by-default safety gates.

No real order path should be enabled until stronger paper evidence, risk gates,
operator controls, rollback plans, and broker-specific safety reviews exist.

## Profitability

This release does not prove profitability.

Profitability must be proven separately with real data, costs, slippage,
drawdown, and forward paper results.
