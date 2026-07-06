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

## Tests

Run the full test suite:

    .\.venv\Scripts\python.exe -m pytest

Run the full test suite shortcut:

    .\hqe_test.bat

Run quick local check shortcut:

    .\hqe_quick_check.bat

This runs Git status, the full test suite, and Git status again.

## Git Check

Check working tree status:

    git status --short

Check Git status shortcut:

    .\hqe_status.bat

## Safety Notes

- Paper trading is local/generated only.
- Paper P&L is simulation only.
- Estimated costs are included in net P&L only.
- Gross P&L excludes costs.
- No broker/FYERS connection is used by the paper demo.
- No live or real market data is used by the paper demo.
- No real orders are placed.
- This is not a profitability claim.
