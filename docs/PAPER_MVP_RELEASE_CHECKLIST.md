# HQE Paper MVP v0.1 Release Checklist

This checklist must pass before tagging the Hunter Quant Engine Paper MVP v0.1
release.

## Safety Gates

- [ ] Paper-only workflow confirmed.
- [ ] No broker order placement in paper workflow.
- [ ] No FYERS live execution in paper workflow.
- [ ] No real-money trading.
- [ ] No profitability claim.
- [ ] Paper PnL labelled as simulation only.
- [ ] Live trading explicitly deferred.

## Code Gates

- [ ] Strategy-to-paper bridge completed.
- [ ] Backtest evidence runner completed.
- [ ] Paper replay journal workflow completed.
- [ ] Friendly summary viewer completed.
- [ ] Friendly runs viewer completed.
- [ ] Cleanup helpers preserve unknown files.
- [ ] Generated reports stay ignored by Git.

## Test Gates

Run these before release:

    .\hqe_quick_check.bat

Expected result:

- targeted module tests pass
- full suite passes
- `git diff --check` passes
- `git status --short` is clean after commit

## Operator Gates

The paper operator should be able to run:

    .\hqe_paper_mvp_operator_demo.bat
    .\hqe_paper_replay_journal_all.bat

The workflow should:

- run paper replay journal demo
- print friendly replay journal summary
- list replay journal runs
- open the replay journal folder

## Evidence Gates

Before live-readiness phase starts:

- [ ] Backtest evidence is generated.
- [ ] Costs and slippage are included.
- [ ] Drawdown is visible.
- [ ] Win/loss/flat/unknown counts are visible.
- [ ] Weak strategy result blocks live trading.

## Release Gates

- [ ] Roadmap says Paper MVP v0.1 scope is frozen.
- [ ] Deferred polish backlog exists.
- [ ] Operator guide exists.
- [ ] Paper operator guide completed.
- [ ] Full suite is green.
- [ ] Release commit is pushed.
- [ ] Git tag is created only after all required gates pass.

## Release Tag

Use a tag name like:

    v0.1-paper-mvp

Do not create the release tag until all checklist items above are complete.
