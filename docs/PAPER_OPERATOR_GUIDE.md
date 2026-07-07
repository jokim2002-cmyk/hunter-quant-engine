# HQE Paper Operator Guide

This is the operator guide for the Hunter Quant Engine Paper MVP v0.1 workflow.

The workflow is paper/simulation only.

It does not place broker orders.
It does not use live market data.
It does not use real money.
It does not claim profitability.

## Daily Local Check

Run:

    .\hqe_quick_check.bat

Expected result:

- full test suite passes
- git status is visible before and after tests
- no generated reports are committed

## Paper MVP Operator Demo

Run:

    .\hqe_paper_mvp_operator_demo.bat

This demo runs the Paper MVP flow:

1. Build an approved option-buy plan.
2. Submit it into the paper session.
3. Close the paper position with a simulated exit.
4. Write paper report files.
5. Write paper backtest evidence files.
6. Print a terminal summary.

Generated files are written under:

    reports\paper_trading\operator_demo

Important outputs:

- strategy-to-paper report text
- strategy-to-paper summary JSON
- paper backtest evidence text
- paper backtest evidence JSON
- evidence manifest JSON

## Replay Journal Workflow

Run:

    .\hqe_paper_replay_journal_all.bat

This workflow:

- runs the paper replay journal demo
- prints a friendly replay journal summary
- lists replay journal runs
- opens the replay journal folder

## Evidence Aggregate

After running the Paper MVP operator demo, aggregate paper evidence:

    .\hqe_paper_evidence_aggregate.bat

This writes aggregate evidence under:

    reports\paper_trading\evidence_aggregate

The aggregate is paper/simulation only and is not a profitability claim.

## Evidence Gates

The evidence runner blocks unsafe live-readiness when:

- closed trades are below the configured minimum
- open positions remain above the configured maximum
- unknown trade results exceed the configured maximum
- simulated net PnL is unavailable or below a configured threshold

Passing evidence gates is not a profitability claim.

## Release Gate

Run:

    .\hqe_paper_mvp_release_check.bat

This checks Paper MVP release readiness. It does not create a git tag.

## Live Safety Lock

Before any future live-readiness engineering work, run:

    .\hqe_live_safety_lock_check.bat

A pass means the live safety lock is closed and dangerous live features are disabled.
It does not approve live trading or real money.

## Live Readiness Gate

After aggregating paper evidence, run:

    .\hqe_live_readiness_check.bat

A pass means only that live-readiness engineering may start.
It does not approve real-money trading.

## Before Live Readiness

Do not move to live-readiness unless:

- Paper MVP operator demo runs successfully.
- Replay journal workflow runs successfully.
- Full quick check passes.
- Evidence report is generated.
- Release checklist is reviewed.
- Live trading remains deferred.
- Live trading remains disabled by default.

## Operator Rule

If a command fails, do not continue to the next phase.

Paste the error, fix the blocker, rerun the command, then continue.
