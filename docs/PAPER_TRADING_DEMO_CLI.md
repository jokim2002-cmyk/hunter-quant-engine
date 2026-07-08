# Paper Trading Demo CLI

Shortcut quick-start card: `../README_SHORTCUTS.md`

This document explains the safe local paper trading demo CLI.

The demo is fake/local only. It does not connect to FYERS, does not use live or real market data, and does not place real orders.

It is not a profitability claim.

---

## Run Command

From the project root:

    .\.venv\Scripts\python.exe -m src.paper_trading.paper_trading_demo_cli

The older example script also works:

    .\.venv\Scripts\python.exe examples\run_paper_trading_demo.py

Paper demo shortcuts:

    .\scripts\paper_trading\hqe_paper_demo.bat
    .\scripts\paper_trading\hqe_paper_report.bat
    .\scripts\paper_trading\hqe_paper_demo_report.bat
    .\scripts\paper_trading\hqe_paper_folder.bat
    .\scripts\paper_trading\hqe_paper_report_text.bat

Shortcut meanings:

- `hqe_paper_demo.bat` runs the safe local paper trading demo.
- `hqe_paper_report.bat` opens the latest generated text report after a demo run.
- `hqe_paper_demo_report.bat` runs the demo and then opens the report.
- `hqe_paper_folder.bat` opens the generated paper trading reports folder.
- `hqe_paper_report_text.bat` prints the latest generated text report in the terminal.

Implementation path:

    src/paper_trading/paper_trading_demo_cli.py

Example wrapper path:

    examples/run_paper_trading_demo.py

---

## What The Demo Does

The demo runs a complete safe local paper flow:

1. Creates a synthetic approved NIFTY CE option-buy trade plan.
2. Converts the trade plan into a paper order request.
3. Submits the request into PaperTradingSession.
4. Closes the fake local paper position.
5. Computes paper-only simulated gross P&L, estimated costs, and simulated net P&L.
6. Safely cleans previous known paper report bundle files.
7. Writes fresh local report files under reports/paper_trading/.
8. Prints a short trader-readable terminal summary.

---

## Generated Report Files

The CLI writes generated files under:

    reports/paper_trading/

Expected files:

    manifest.json
    summary.json
    summary.csv
    orders.json
    orders.csv
    open_positions.json
    open_positions.csv
    exit_records.json
    exit_records.csv
    report.txt

The reports/ directory is generated output and should stay ignored by Git.

---

## Report Manifest

The report bundle includes:

    reports/paper_trading/manifest.json

The manifest records:

- report_version
- report_source
- generated_at
- paper_pnl_is_simulation_only
- output_dir
- generated report file paths

This makes each local paper report bundle easier to inspect and trace.

---

## Cleanup Behavior

Before writing a fresh report bundle, the CLI calls the safe cleanup helper.

The cleanup helper deletes only known generated paper report files:

    manifest.json
    summary.json
    summary.csv
    orders.json
    orders.csv
    open_positions.json
    open_positions.csv
    exit_records.json
    exit_records.csv
    report.txt

Unknown files in the report folder are left untouched.

Cleanup is only allowed under a path containing reports/.

---

## Terminal Output

The CLI prints a concise summary, including:

    fake/local paper trading demo
    synthetic option-buy trade plan
    paper trade symbol: NIFTY26JUL24200CE
    paper trade quantity: 130
    paper entry premium: 100.0
    paper simulated exit premium: 135.0
    paper simulated gross pnl: 4550.0
    paper estimated costs: 53.0
    paper simulated net pnl: 4497.0
    paper report output dir: reports/paper_trading
    paper report text: reports/paper_trading/report.txt
    paper report files are local/generated

The exact generated timestamp in report files changes per run.

---

## Safety Limits

This CLI must remain paper/local only.

Binding safety rules:

- No broker SDK import.
- No FYERS integration.
- No live market data.
- No real market data.
- No real orders.
- No option selling.
- No futures execution.
- No equity execution.
- No profitability claim.

The demo uses synthetic prices and simulated costs only.

---

## Recommended Validation

After changing paper demo CLI behavior, run:

    .\.venv\Scripts\python.exe -m pytest tests\paper_trading\test_paper_trading_demo_cli.py tests\examples\test_run_paper_trading_demo.py

Before committing, run the full suite:

    .\.venv\Scripts\python.exe -m pytest

No milestone is complete unless tests pass and Git is clean.
