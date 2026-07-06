"""
Run Offline Option Buy Backtest Script Tests
"""

from pathlib import Path

import pytest

import scripts.run_option_buy_backtest as cli_module
from scripts.run_option_buy_backtest import format_summary, main, run_backtest
from src.backtesting.option_buy_backtest_summary import OptionBuyBacktestSummary


SCENARIO_CSV = """
snapshot_id,timestamp,signal_type,signal_strength,confidence,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,rationale
s1,2026-07-06T09:15:00,long,strong,0.9,NIFTY,24210,2026-07-09,24200,CE,65,NIFTY26JUL24200CE,100,99,100,10000,50000,test setup
"""

PREMIUM_CSV = """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:20:00,100,170,95,165,1000
"""


def _write_csv(tmp_path, filename, content):
    csv_path = tmp_path / filename
    csv_path.write_text(content.strip() + "\n", encoding="utf-8")
    return csv_path


def _summary(rejection_reasons=()):
    return OptionBuyBacktestSummary(
        planned_signals=1,
        rejected_plans=0,
        failed_backtests=0,
        results=(),
        rejection_reasons=rejection_reasons,
    )


def test_format_summary_includes_core_summary_fields():
    report = format_summary(_summary())

    assert "Hunter Quant Engine - Offline Option Buy Backtest" in report
    assert "Planned signals: 1" in report
    assert "Completed trades: 0" in report
    assert "Rejected plans: 0" in report
    assert "Failed backtests: 0" in report
    assert "Winning trades: 0" in report
    assert "Losing trades: 0" in report
    assert "Breakeven trades: 0" in report
    assert "Total gross P&L: 0.00" in report
    assert "Total estimated charges: 0.00" in report
    assert "Total net P&L: 0.00" in report


def test_format_summary_formats_win_rate_as_percent_with_two_decimals(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    report = format_summary(run_backtest(scenario_csv, premium_csv))

    assert "Win rate: 100.00%" in report


def test_format_summary_includes_rejection_reasons_when_present():
    report = format_summary(_summary(rejection_reasons=("setup rejected",)))

    assert "Rejection reasons:" in report
    assert "- setup rejected" in report


def test_run_backtest_loads_csv_files_and_returns_summary(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    summary = run_backtest(scenario_csv, premium_csv)

    assert summary.planned_signals == 1
    assert summary.completed_trades == 1
    assert summary.winning_trades == 1


def test_main_returns_zero_for_valid_csv_inputs(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
        ]
    )

    assert exit_code == 0


def test_main_prints_summary_for_valid_csv_inputs(tmp_path, capsys):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
        ]
    )

    output = capsys.readouterr().out
    assert "Hunter Quant Engine - Offline Option Buy Backtest" in output
    assert "Completed trades: 1" in output


def test_main_fails_through_argparse_when_required_args_missing():
    with pytest.raises(SystemExit):
        main([])


def test_script_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(cli_module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
