# HQE Paper MVP v0.1 Release Notes

Hunter Quant Engine Paper MVP v0.1 is the first frozen paper-only release.

This release closes the paper trading infrastructure phase and prepares the
project for the next evidence/live-readiness phase.

## Safety Boundary

Paper MVP v0.1 is paper/simulation only.

It does not place broker orders.
It does not use live market data.
It does not use real money.
It does not claim profitability.

Live trading remains deferred until evidence gates and live-readiness gates pass.

## Completed Paper MVP Modules

Paper MVP v0.1 includes:

- Option-buy trade plan to paper order conversion.
- Paper order journal.
- Paper position state.
- Paper trading session.
- Paper close-position flow.
- Paper exit records.
- Simulated gross PnL.
- Estimated costs and simulated net PnL.
- Paper trading report writer.
- Paper trading replay loop.
- Paper replay journal persistence.
- Paper replay journal cleanup.
- Paper replay journal index.
- Friendly replay journal summary viewer.
- Friendly replay journal runs viewer.
- Strategy-to-paper bridge.
- Paper backtest evidence runner.
- Paper MVP operator demo workflow.
- Paper MVP release gate.

## Main Operator Commands

Run the full local check:

    .\scripts\paper_trading\hqe_quick_check.bat

Run the Paper MVP operator demo:

    .\scripts\paper_trading\hqe_paper_mvp_operator_demo.bat

Run the replay journal workflow:

    .\scripts\paper_trading\hqe_paper_replay_journal_all.bat

Run the release gate:

    .\scripts\paper_trading\hqe_paper_mvp_release_check.bat

## Release Tag

Release tag name:

    v0.1-paper-mvp

The release tag is created only after:

- full quick check passes
- Paper MVP operator demo passes
- replay journal workflow passes
- release gate passes
- release-close commit is pushed

## Next Phase

After Paper MVP v0.1:

1. Collect stronger historical evidence.
2. Add stricter live-readiness gates.
3. Keep live broker execution disabled by default.
4. Avoid real-money trading until data supports the strategy.
5. Bundle polish work instead of doing micro-polish commits.

## Profitability

This release does not prove profitability.

Profitability must be proven separately with real data, costs, slippage,
drawdown, and forward paper results.
