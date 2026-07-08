# Paper Trading Replay Journal

This guide explains the safe local paper replay journal workflow.

The replay journal workflow is fake/local paper trading only.

It does not connect to a broker.

It does not use live market data.

It does not place real orders.

It is not a profitability claim.

Paper P&L is simulation only.

---

## What This Workflow Does

The replay journal workflow runs deterministic paper replay steps and persists the resulting paper session under `reports/`.

It can:

- submit fake/paper orders
- close fake/paper positions
- record fake/paper exit records
- calculate simulated gross P&L
- calculate estimated costs
- calculate simulated net P&L
- write a local paper journal bundle
- print the replay journal summary
- open the replay journal folder

---

## Main Shortcut

Run the full workflow:

    .\scripts\paper_trading\hqe_paper_replay_journal_all.bat

This shortcut runs:

The all-in-one shortcut uses the pretty runs viewer instead of raw index JSON.

    .\scripts\paper_trading\hqe_paper_replay_journal.bat
    .\scripts\paper_trading\hqe_paper_replay_journal_summary.bat
    .\scripts\paper_trading\hqe_paper_replay_journal_summary.bat
    .\scripts\paper_trading\hqe_paper_replay_journal_runs.bat
    .\scripts\paper_trading\hqe_paper_replay_journal_folder.bat

---

## Individual Shortcuts

Run fake paper replay and save the journal bundle:

    .\scripts\paper_trading\hqe_paper_replay_journal.bat

Print the generated summary:

The summary shortcut uses a friendly terminal view instead of raw summary JSON.

    .\scripts\paper_trading\hqe_paper_replay_journal_summary.bat

Print the generated index JSON:

    .\scripts\paper_trading\hqe_paper_replay_journal_index.bat

List replay journal runs:

    .\scripts\paper_trading\hqe_paper_replay_journal_runs.bat

Open the generated replay journal folder:

    .\scripts\paper_trading\hqe_paper_replay_journal_folder.bat

---

## Generated Local Files

The demo replay journal run writes files under:

    reports/paper_trading/journal/demo-replay-journal/

Expected generated files:

- `metadata.json`
- `summary.json`
- `orders.json`
- `open_positions.json`
- `exit_records.json`
- `manifest.json`
- `index.json`

These files are local/generated outputs and must stay ignored by Git.

The index file tracks available replay journal runs.

---

## Python Entry Point

The shortcut runs this module:

    .\.venv\Scripts\python.exe -m src.paper_trading.paper_trading_replay_journal_demo_cli

Core helpers:

- `src/paper_trading/paper_trading_replay_loop.py`
- `src/paper_trading/paper_trading_journal_store.py`
- `src/paper_trading/paper_trading_replay_journal.py`
- `src/paper_trading/paper_trading_replay_journal_demo_cli.py`

---

## Safety Rules

This workflow must remain safe and local.

Required rules:

- no broker connection
- no FYERS connection
- no live market data dependency
- no real order placement
- no fake profitability claim
- paper P&L must remain clearly simulation only
- estimated costs must be included in net P&L only
- gross P&L must exclude costs

---

## Recommended Manual Check

Run:

    .\scripts\paper_trading\hqe_paper_replay_journal_all.bat

Then verify:

    reports/paper_trading/journal/demo-replay-journal/summary.json

The summary should show:

- `total_orders`
- `closed_trades_count`
- `total_simulated_gross_pnl`
- `total_estimated_costs`
- `total_simulated_net_pnl`
- `paper_pnl_is_simulation_only`

---

## What This Unlocks Next

This workflow prepares HQE for:

1. replaying multiple paper trade steps
2. saving every replay run by run id
3. comparing paper journal runs over time
4. building a cleaner paper dashboard/report
5. later connecting replay logic to real option premium replay data

Real-money execution remains the final phase only.
