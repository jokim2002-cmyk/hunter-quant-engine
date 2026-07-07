# HQE Shortcuts Quick Start

This is the daily-use command card for safe local HQE checks.

Detailed paper trading demo CLI guide: `docs/PAPER_TRADING_DEMO_CLI.md`

## Help

Show safe local shortcuts:

    .\hqe_help.bat

## Paper Trading Demo

Run the safe local paper trading demo:

    .\hqe_paper_demo.bat

Open the latest generated paper trading report:

    .\hqe_paper_report.bat

Run the demo and then open the generated report:

    .\hqe_paper_demo_report.bat

Open the generated paper trading reports folder:

    .\hqe_paper_folder.bat

Print the latest generated paper trading report in the terminal:

    .\hqe_paper_report_text.bat

## Tests

Run the full test suite:

    .\.venv\Scripts\python.exe -m pytest

Run the full test suite shortcut:

    .\hqe_test.bat

Run quick local check shortcut:

    .\hqe_quick_check.bat

This runs Git status, the full test suite, and Git status again.

Run the daily workflow shortcut:

    .\hqe_daily.bat

This runs the quick local check, then runs the paper demo and opens the generated report.

## Git Check

Check working tree status:

    git status --short

Check Git status shortcut:

    .\hqe_status.bat

Show repo snapshot shortcut:

    .\hqe_snapshot.bat

This shows the current branch, latest commits, and working tree status.

## Safety Notes

- Paper trading is local/generated only.
- Paper P&L is simulation only.
- Estimated costs are included in net P&L only.
- Gross P&L excludes costs.
- No broker/FYERS connection is used by the paper demo.
- No live or real market data is used by the paper demo.
- No real orders are placed.
- This is not a profitability claim.
- `hqe_paper_replay_journal_summary.bat` - print friendly replay journal summary
- `hqe_paper_replay_journal_index.bat` - print replay journal index
- `hqe_paper_replay_journal_runs.bat` - list replay journal runs
- `hqe_paper_mvp_operator_demo.bat` - run Paper MVP operator demo
- `hqe_paper_mvp_release_check.bat` - run Paper MVP release gate
- `hqe_paper_evidence_aggregate.bat` - aggregate paper evidence
- `hqe_live_readiness_check.bat` - check live-readiness gate
- `hqe_live_safety_lock_check.bat` - check disabled live safety lock
- `hqe_live_readiness_preflight.bat` - run full live-readiness preflight
- `hqe_paper_replay_journal_all.bat` - run replay journal, print summary/runs, and open folder

See also: `docs/PAPER_TRADING_REPLAY_JOURNAL.md`
