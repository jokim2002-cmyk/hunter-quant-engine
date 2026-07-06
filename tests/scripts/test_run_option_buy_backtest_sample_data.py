from pathlib import Path

from scripts.run_option_buy_backtest import format_summary, main, run_backtest
from src.backtesting.option_buy_backtest_scenario_csv_loader import (
    OptionBuyBacktestScenarioCsvLoader,
)


SAMPLE_DIR = Path("examples/option_buy_backtest")
SCENARIO_CSV = SAMPLE_DIR / "sample_scenario.csv"
SIGNALS_CSV = SAMPLE_DIR / "sample_signals.csv"
SNAPSHOTS_CSV = SAMPLE_DIR / "sample_snapshots.csv"
PREMIUM_CSV = SAMPLE_DIR / "sample_premium.csv"
README = SAMPLE_DIR / "README.md"


def test_sample_scenario_csv_exists():
    assert SCENARIO_CSV.exists()


def test_sample_premium_csv_exists():
    assert PREMIUM_CSV.exists()


def test_sample_signal_csv_exists():
    assert SIGNALS_CSV.exists()


def test_sample_snapshot_csv_exists():
    assert SNAPSHOTS_CSV.exists()


def test_run_backtest_works_with_sample_files():
    summary = run_backtest(SCENARIO_CSV, PREMIUM_CSV)

    assert summary.planned_signals == len(
        OptionBuyBacktestScenarioCsvLoader().load_scenarios(SCENARIO_CSV)
    )
    assert summary.completed_trades >= 1


def test_format_summary_includes_core_sample_result_fields():
    summary_text = format_summary(run_backtest(SCENARIO_CSV, PREMIUM_CSV))

    assert "Hunter Quant Engine - Offline Option Buy Backtest" in summary_text
    assert "Planned signals:" in summary_text
    assert "Completed trades:" in summary_text
    assert "Total net P&L:" in summary_text


def test_main_returns_zero_for_sample_files():
    exit_code = main(
        [
            "--scenario-csv",
            str(SCENARIO_CSV),
            "--premium-csv",
            str(PREMIUM_CSV),
        ]
    )

    assert exit_code == 0


def test_main_returns_zero_for_signal_and_snapshot_sample_files():
    exit_code = main(
        [
            "--signal-csv",
            str(SIGNALS_CSV),
            "--snapshot-csv",
            str(SNAPSHOTS_CSV),
            "--premium-csv",
            str(PREMIUM_CSV),
        ]
    )

    assert exit_code == 0


def test_run_backtest_works_with_signal_and_snapshot_sample_files():
    summary = run_backtest(
        signal_csv=str(SIGNALS_CSV),
        snapshot_csv=str(SNAPSHOTS_CSV),
        premium_csv=str(PREMIUM_CSV),
    )

    assert summary.planned_signals >= 1
    assert summary.completed_trades >= 1


def test_sample_readme_states_synthetic_demo_and_no_profitability_claim():
    readme = README.read_text(encoding="utf-8").lower()

    assert "synthetic/demo" in readme
    assert "not real market data" in readme
    assert "not a profitability claim" in readme


def test_sample_readme_includes_all_report_output_examples():
    readme = README.read_text(encoding="utf-8")

    assert "--summary-json" in readme
    assert "--summary-csv" in readme
    assert "--trades-json" in readme
    assert "--trades-csv" in readme
    assert "--signal-csv" in readme
    assert "--snapshot-csv" in readme


def test_gitignore_ignores_generated_reports_but_not_sample_csvs():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "reports/" in gitignore
    assert "*.generated.json" in gitignore
    assert "*.generated.csv" in gitignore
    assert "examples/option_buy_backtest/*.csv" not in gitignore
    assert "examples/option_buy_backtest/sample_scenario.csv" not in gitignore
    assert "examples/option_buy_backtest/sample_premium.csv" not in gitignore