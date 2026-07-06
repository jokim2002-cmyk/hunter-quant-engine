# HQE Paper MVP v0.1 Scope Freeze

This document freezes the Hunter Quant Engine paper trading MVP scope.

The goal is to stop infinite micro-polish and move the project toward a complete,
testable paper trading release.

## Status

Paper MVP v0.1 is a paper-only release target.

It is not live trading.
It does not place broker orders.
It does not use real money.
It does not claim profitability.

## Included in Paper MVP v0.1

The Paper MVP includes these completed or required capabilities:

- Offline option market data polling, recording, replay, and validation workflow.
- Option-buy backtest readiness workflow.
- Option-buy trade plan to paper order request conversion.
- Paper order journal.
- Paper position state.
- Paper trading session.
- Paper close-position flow.
- Paper exit records.
- Simulated paper gross PnL.
- Estimated costs and simulated paper net PnL.
- Paper trading report writer.
- Paper trading demo CLI and shortcuts.
- Paper trading replay loop.
- Strategy-to-paper bridge.
- Backtest evidence runner.
- Paper MVP operator demo workflow.
- Paper MVP release gate.
- Paper replay journal persistence.
- Paper replay journal cleanup.
- Paper replay journal index.
- Friendly replay journal summary viewer.
- Friendly replay journal runs viewer.

## Must Finish Before v0.1 Release

Only these roadmap items can block Paper MVP v0.1:

No remaining code/documentation blockers before the Paper MVP v0.1 release tag.

The release tag is created only after final green checks pass.

## Deferred Beyond v0.1

These items are intentionally not part of Paper MVP v0.1:

- Live broker order placement.
- Real-money trading.
- FYERS live execution.
- Auto-trading without manual review.
- Profitability claims.
- Dashboard/UI polish.
- Advanced report styling.
- Non-blocking shortcut polish.
- Cosmetic docs polish.

## Quality Rules

Fast module mode is allowed, but quality cannot be reduced.

Every roadmap-closing module must:

- Start from a clean git status.
- Avoid blind edits.
- Prefer read-only audit before a large module patch.
- Add or update tests for behavior and safety.
- Run targeted tests.
- Run the full quick check.
- Run `git diff --check`.
- Commit only after green tests.
- Push only after the clean commit is created.

## No Micro-Polish Rule

No more one-small-shortcut or one-small-doc polish commits while Paper MVP v0.1
is not closed.

Polish is allowed only as a bundled polish module after the end-to-end paper
trading module runs successfully.

## Paper MVP Definition of Done

Paper MVP v0.1 is done when a user can run one documented workflow that:

1. Takes approved strategy output or replay input.
2. Creates paper orders.
3. Updates paper positions.
4. Records paper exits.
5. Writes paper reports.
6. Writes replay journal files.
7. Lists replay journal runs.
8. Shows friendly paper summary output.
9. Requires no broker.
10. Requires no live market data.
11. Places no real orders.

## Live Trading Boundary

Live trading starts only after Paper MVP v0.1 and evidence gates are complete.

The project can reach live-readiness engineering, but profitable live trading is
not guaranteed. Profitability must be proven with data, costs, slippage, and
forward paper results.
