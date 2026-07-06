from pathlib import Path

from scripts.run_option_buy_backtest import format_summary, main, run_backtest
from src.backtesting.option_buy_backtest_scenario_csv_loader import (
    OptionBuyBacktestScenarioCsvLoader,
)


SAMPLE_DIR = Path("examples/option_buy_backtest")
SCENARIO_CSV = SAMPLE_DIR / "sample_scenario.csv"
PREMIUM_CSV = SAMPLE_DIR / "sample_premium.csv"
README = SAMPLE_DIR / "README.md"


def test_sample_scenario_csv_exists():
    assert SCENARIO_CSV.exists()


def test_sample_premium_csv_exists():
    assert PREMIUM_CSV.exists()


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


def test_sample_readme_states_synthetic_demo_and_no_profitability_claim():
    readme = README.read_text(encoding="utf-8").lower()

    assert "synthetic/demo" in readme
    assert "not real market data" in readme
    assert "not a profitability claim" in readme