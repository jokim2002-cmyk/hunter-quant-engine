"""
Run Offline Option Buy Backtest Script Tests
"""

import csv
import json
from pathlib import Path

import pytest

import scripts.run_option_buy_backtest as cli_module
from scripts.run_option_buy_backtest import (
    format_summary,
    main,
    run_backtest,
    summary_to_dict,
    write_summary_csv,
    write_summary_json,
)
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


def test_summary_to_dict_contains_expected_summary_fields():
    summary = _summary(rejection_reasons=("setup rejected", "bad data"))

    payload = summary_to_dict(summary)

    assert payload["planned_signals"] == 1
    assert payload["completed_trades"] == 0
    assert payload["rejected_plans"] == 0
    assert payload["failed_backtests"] == 0
    assert payload["winning_trades"] == 0
    assert payload["losing_trades"] == 0
    assert payload["breakeven_trades"] == 0
    assert payload["win_rate"] == 0.0
    assert payload["total_gross_pnl"] == 0.0
    assert payload["total_estimated_charges"] == 0.0
    assert payload["total_net_pnl"] == 0.0
    assert payload["rejection_reasons"] == ["setup rejected", "bad data"]


def test_write_summary_json_creates_parent_directories_and_writes_json(tmp_path):
    summary = _summary(rejection_reasons=("setup rejected",))
    output_path = tmp_path / "nested" / "summary.json"

    write_summary_json(summary, output_path)

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["planned_signals"] == 1
    assert payload["rejection_reasons"] == ["setup rejected"]


def test_write_summary_csv_creates_parent_directories_and_writes_csv(tmp_path):
    summary = _summary(rejection_reasons=("setup rejected", "bad data"))
    output_path = tmp_path / "nested" / "summary.csv"

    write_summary_csv(summary, output_path)

    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == [
        "planned_signals",
        "completed_trades",
        "rejected_plans",
        "failed_backtests",
        "winning_trades",
        "losing_trades",
        "breakeven_trades",
        "win_rate",
        "total_gross_pnl",
        "total_estimated_charges",
        "total_net_pnl",
        "rejection_reasons",
    ]
    assert rows[1][11] == "setup rejected;bad data"


def test_main_writes_json_when_requested(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "summary.json"

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
            "--summary-json",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["completed_trades"] == 1


def test_main_writes_csv_when_requested(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "summary.csv"

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
            "--summary-csv",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[1][0] == "1"


def test_main_writes_both_json_and_csv_when_requested(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    json_path = tmp_path / "reports" / "summary.json"
    csv_path = tmp_path / "reports" / "summary.csv"

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
            "--summary-json",
            str(json_path),
            "--summary-csv",
            str(csv_path),
        ]
    )

    assert exit_code == 0
    assert json_path.exists()
    assert csv_path.exists()


def test_main_without_output_args_still_prints_summary_and_returns_zero(tmp_path, capsys):
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
    output = capsys.readouterr().out
    assert "Hunter Quant Engine - Offline Option Buy Backtest" in output


def test_script_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(cli_module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
