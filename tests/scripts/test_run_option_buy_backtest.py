"""
Run Offline Option Buy Backtest Script Tests
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path

import pytest

import scripts.run_option_buy_backtest as cli_module
from scripts.run_option_buy_backtest import (
    format_summary,
    main,
    run_backtest,
    summary_to_dict,
    trade_result_to_dict,
    trade_results_to_dicts,
    write_summary_csv,
    write_summary_json,
    write_trades_csv,
    write_trades_json,
)
from src.backtesting.option_buy_backtest_summary import OptionBuyBacktestSummary
from src.backtesting.option_premium_backtest_exit_reason import (
    OptionPremiumBacktestExitReason,
)
from src.backtesting.option_premium_backtest_result import OptionPremiumBacktestResult
from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


SCENARIO_CSV = """
snapshot_id,timestamp,signal_type,signal_strength,confidence,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,rationale
s1,2026-07-06T09:15:00,long,strong,0.9,NIFTY,24210,2026-07-09,24200,CE,65,NIFTY26JUL24200CE,100,99,100,10000,50000,test setup
"""

SIGNAL_CSV = """
timestamp,signal_type,signal_strength,confidence,rationale
2026-07-06T09:15:00,long,strong,0.9,test setup
"""

SNAPSHOT_CSV = """
snapshot_id,timestamp,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,delta,theta,vega,gamma,implied_volatility
s1,2026-07-06T09:15:00,NIFTY,24210,2026-07-09,24200,CE,65,NIFTY26JUL24200CE,100,99,100,10000,50000,,,,,
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


def test_main_returns_zero_for_signal_and_snapshot_csv_inputs(tmp_path):
    signal_csv = _write_csv(tmp_path, "signals.csv", SIGNAL_CSV)
    snapshot_csv = _write_csv(tmp_path, "snapshots.csv", SNAPSHOT_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    exit_code = main(
        [
            "--signal-csv",
            str(signal_csv),
            "--snapshot-csv",
            str(snapshot_csv),
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


def test_main_rejects_missing_signal_and_snapshot_inputs(tmp_path):
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    with pytest.raises(SystemExit):
        main(["--premium-csv", str(premium_csv)])


def test_main_rejects_scenario_csv_mixed_with_signal_csv(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    signal_csv = _write_csv(tmp_path, "signals.csv", SIGNAL_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    with pytest.raises(SystemExit):
        main([
            "--scenario-csv",
            str(scenario_csv),
            "--signal-csv",
            str(signal_csv),
            "--premium-csv",
            str(premium_csv),
        ])


def test_main_rejects_scenario_csv_mixed_with_snapshot_csv(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    snapshot_csv = _write_csv(tmp_path, "snapshots.csv", SNAPSHOT_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    with pytest.raises(SystemExit):
        main([
            "--scenario-csv",
            str(scenario_csv),
            "--snapshot-csv",
            str(snapshot_csv),
            "--premium-csv",
            str(premium_csv),
        ])


def test_main_rejects_signal_csv_without_snapshot_csv(tmp_path):
    signal_csv = _write_csv(tmp_path, "signals.csv", SIGNAL_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    with pytest.raises(SystemExit):
        main([
            "--signal-csv",
            str(signal_csv),
            "--premium-csv",
            str(premium_csv),
        ])


def test_main_rejects_snapshot_csv_without_signal_csv(tmp_path):
    snapshot_csv = _write_csv(tmp_path, "snapshots.csv", SNAPSHOT_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    with pytest.raises(SystemExit):
        main([
            "--snapshot-csv",
            str(snapshot_csv),
            "--premium-csv",
            str(premium_csv),
        ])


def _backtest_result():
    plan = OptionBuyTradePlan(
        signal=TradeSignal(
            signal_type=SignalType.LONG,
            strength=SignalStrength.STRONG,
            confidence=0.9,
            rationale=("test",),
            created_at=datetime(2026, 7, 6, 10, 15),
        ),
        entry=OptionChainEntry(
            contract=OptionContract(
                underlying_symbol="NIFTY",
                expiry_date=date(2026, 7, 9),
                strike_price=24200.0,
                option_type=OptionType.CE,
                lot_size=65,
                symbol="NIFTY26JUL24200CE",
            ),
            last_traded_price=100.0,
            bid_price=99.0,
            ask_price=101.0,
            volume=10000,
            open_interest=50000,
        ),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=1,
        estimated_charges=10.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )
    return OptionPremiumBacktestResult(
        plan=plan,
        exit_reason=OptionPremiumBacktestExitReason.TARGET_HIT,
        exit_premium=160.0,
        bars_held=2,
        estimated_charges=10.0,
    )


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


def test_main_writes_summary_csv_in_signal_and_snapshot_mode(tmp_path):
    signal_csv = _write_csv(tmp_path, "signals.csv", SIGNAL_CSV)
    snapshot_csv = _write_csv(tmp_path, "snapshots.csv", SNAPSHOT_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "summary.csv"

    exit_code = main(
        [
            "--signal-csv",
            str(signal_csv),
            "--snapshot-csv",
            str(snapshot_csv),
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


def test_trade_result_to_dict_returns_expected_fields():
    payload = trade_result_to_dict(_backtest_result())

    assert payload["symbol"] == "NIFTY26JUL24200CE"
    assert payload["option_type"] == "CE"
    assert payload["strike_price"] == 24200.0
    assert payload["expiry_date"] == "2026-07-09"
    assert payload["entry_premium"] == 100.0
    assert payload["stop_loss_premium"] == 70.0
    assert payload["target_premium"] == 160.0
    assert payload["exit_premium"] == 160.0
    assert payload["exit_reason"] == "target_hit"
    assert payload["quantity"] == 65
    assert payload["bars_held"] == 2
    assert payload["estimated_charges"] == 10.0
    assert payload["gross_pnl"] == 3900.0
    assert payload["net_pnl"] == 3890.0
    assert payload["return_percent"] == 0.6
    assert payload["is_win"] is True
    assert payload["is_loss"] is False


def test_trade_results_to_dicts_returns_list_of_dicts():
    payloads = trade_results_to_dicts([_backtest_result()])

    assert len(payloads) == 1
    assert payloads[0]["symbol"] == "NIFTY26JUL24200CE"


def test_write_trades_json_creates_json_file(tmp_path):
    output_path = tmp_path / "nested" / "trades.json"

    write_trades_json([_backtest_result()], output_path)

    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["symbol"] == "NIFTY26JUL24200CE"


def test_write_trades_csv_creates_csv_file_with_header_and_trade_row(tmp_path):
    output_path = tmp_path / "nested" / "trades.csv"

    write_trades_csv([_backtest_result()], output_path)

    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0][0] == "symbol"
    assert rows[1][0] == "NIFTY26JUL24200CE"


def test_main_writes_trades_json_when_requested(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "trades.json"

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
            "--trades-json",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["symbol"] == "NIFTY26JUL24200CE"


def test_main_writes_trades_json_in_signal_and_snapshot_mode(tmp_path):
    signal_csv = _write_csv(tmp_path, "signals.csv", SIGNAL_CSV)
    snapshot_csv = _write_csv(tmp_path, "snapshots.csv", SNAPSHOT_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "trades.json"

    exit_code = main(
        [
            "--signal-csv",
            str(signal_csv),
            "--snapshot-csv",
            str(snapshot_csv),
            "--premium-csv",
            str(premium_csv),
            "--trades-json",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["symbol"] == "NIFTY26JUL24200CE"


def test_main_writes_trades_csv_when_requested(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "trades.csv"

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
            "--trades-csv",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[1][0] == "NIFTY26JUL24200CE"


def test_main_writes_trades_csv_in_signal_and_snapshot_mode(tmp_path):
    signal_csv = _write_csv(tmp_path, "signals.csv", SIGNAL_CSV)
    snapshot_csv = _write_csv(tmp_path, "snapshots.csv", SNAPSHOT_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    output_path = tmp_path / "reports" / "trades.csv"

    exit_code = main(
        [
            "--signal-csv",
            str(signal_csv),
            "--snapshot-csv",
            str(snapshot_csv),
            "--premium-csv",
            str(premium_csv),
            "--trades-csv",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[1][0] == "NIFTY26JUL24200CE"


def test_main_can_write_summary_and_trades_outputs_in_one_run(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)
    summary_json_path = tmp_path / "reports" / "summary.json"
    summary_csv_path = tmp_path / "reports" / "summary.csv"
    trades_json_path = tmp_path / "reports" / "trades.json"
    trades_csv_path = tmp_path / "reports" / "trades.csv"

    exit_code = main(
        [
            "--scenario-csv",
            str(scenario_csv),
            "--premium-csv",
            str(premium_csv),
            "--summary-json",
            str(summary_json_path),
            "--summary-csv",
            str(summary_csv_path),
            "--trades-json",
            str(trades_json_path),
            "--trades-csv",
            str(trades_csv_path),
        ]
    )

    assert exit_code == 0
    assert summary_json_path.exists()
    assert summary_csv_path.exists()
    assert trades_json_path.exists()
    assert trades_csv_path.exists()


def test_script_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(cli_module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
