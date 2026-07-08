# Laptop to PC Handoff

This handoff is for syncing laptop work to the PC before running heavy HQE research commands.

## Latest Laptop State

- Latest pushed commit: 0b2eedf Update project requirements
- Tests on laptop: 620 passed
- Laptop git status: clean
- Branch: master
- Remote: origin/master

## Machine Rule

Laptop:

- Code changes
- Documentation
- Unit tests
- Full pytest
- Dry-runs only
- Git commit and push

PC:

- Pull latest code
- Full pytest after pull
- Full FYERS real-data strategy mode benchmark
- Full strategy experiment execution
- Heavy research runs

Do not run these on laptop:

- hqe_benchmark_modes.bat
- hqe_run_experiments.bat
- py scripts\run_strategy_experiments.py --execute
- py scripts\benchmark_strategy_modes.py --input "data\raw\fyers_nifty_5min.csv"

## PC Pull Steps

Open PowerShell on PC:

cd /d "D:\Hunter_Quant_Engine_PC_TRANSFER"
git status --short

If status is clean:

git pull --ff-only

Then run tests:

.\.venv\Scripts\python.exe -m pytest

## PC Heavy Run Order

First run strategy mode benchmark:

.\hqe_benchmark_modes.bat

Then inspect:

Get-Content "data\processed\fyers_nifty_5m_mode_benchmark_report.txt"
Get-Content "data\processed\fyers_nifty_5m_mode_benchmark_summary.csv"

Then run strategy experiments:

.\hqe_run_experiments.bat

Then inspect:

Get-Content "data\processed\strategy_experiment_report.txt"
Get-Content "data\processed\strategy_experiment_summary.csv"

Finally check:

git status --short

## Do Not Commit Generated Outputs

These generated outputs are ignored and should not be committed:

- data/processed/fyers_nifty_5m_strict_*
- data/processed/fyers_nifty_5m_balanced_*
- data/processed/fyers_nifty_5m_relaxed_*
- data/processed/*mode_benchmark*
- data/processed/experiments/
- data/processed/strategy_experiment_report.txt
- data/processed/strategy_experiment_summary.csv

## Result Review Rule

Judge results using:

- net PnL after costs
- return percent
- alpha vs buy-and-hold
- trade count
- total charges
- best/worst experiment rankings

Do not judge using gross PnL only.

No fake profit claims.

## Current PC Goal

The immediate PC goal is to answer:

- Which mode performs best: strict, balanced, or relaxed?
- Does any mode beat buy-and-hold after costs?
- Do experiment rankings reveal a better starting point?
- What should be improved next before walk-forward testing?
