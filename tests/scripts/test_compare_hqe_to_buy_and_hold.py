"""
Tests for HQE buy-and-hold benchmark comparison.
"""

from pathlib import Path

import pytest

from scripts.compare_hqe_to_buy_and_hold import (
    BuyAndHoldResult,
    StrategyResult,
    build_report,
    calculate_buy_and_hold,
    compare_strategy_to_benchmark,
    load_close_prices,
    load_strategy_result,
    write_summary_csv,
)


def test_calculate_buy_and_hold_positive_return():
    result = calculate_buy_and_hold([100.0, 110.0], 10000.0)

    assert result == BuyAndHoldResult(
        starting_balance=10000.0,
        first_close=100.0,
        last_close=110.0,
        units=100.0,
        ending_balance=11000.0,
        net_pnl=1000.0,
        return_percent=10.0,
    )


def test_calculate_buy_and_hold_rejects_missing_data():
    with pytest.raises(ValueError, match="At least two close prices"):
        calculate_buy_and_hold([100.0], 10000.0)


def test_calculate_buy_and_hold_rejects_non_positive_first_close():
    with pytest.raises(ValueError, match="First close price"):
        calculate_buy_and_hold([0.0, 100.0], 10000.0)


def test_load_close_prices_reads_utf8_sig_csv(tmp_path: Path):
    market_csv = tmp_path / "market.csv"
    market_csv.write_text(
        "\ufeffdatetime,open,high,low,close,volume\n"
        "2026-01-01 09:15:00,1,2,0.5,100,10\n"
        "2026-01-01 09:20:00,1,2,0.5,105,10\n",
        encoding="utf-8",
    )

    assert load_close_prices(market_csv) == [100.0, 105.0]


def test_load_strategy_result_reads_last_ending_balance(tmp_path: Path):
    equity_curve_csv = tmp_path / "equity.csv"
    equity_curve_csv.write_text(
        "trade_number,ending_balance\n"
        "1,10100\n"
        "2,10300\n",
        encoding="utf-8",
    )

    result = load_strategy_result(equity_curve_csv, 10000.0)

    assert result == StrategyResult(
        starting_balance=10000.0,
        ending_balance=10300.0,
        net_pnl=300.0,
        return_percent=3.0,
        total_trades=2,
    )


def test_load_strategy_result_handles_no_trades(tmp_path: Path):
    equity_curve_csv = tmp_path / "equity.csv"
    equity_curve_csv.write_text("trade_number,ending_balance\n", encoding="utf-8")

    result = load_strategy_result(equity_curve_csv, 10000.0)

    assert result == StrategyResult(
        starting_balance=10000.0,
        ending_balance=10000.0,
        net_pnl=0.0,
        return_percent=0.0,
        total_trades=0,
    )


def test_compare_strategy_to_benchmark_underperformance():
    strategy = StrategyResult(
        starting_balance=10000.0,
        ending_balance=10500.0,
        net_pnl=500.0,
        return_percent=5.0,
        total_trades=3,
    )
    benchmark = calculate_buy_and_hold([100.0, 110.0], 10000.0)

    comparison = compare_strategy_to_benchmark(strategy, benchmark)

    assert comparison.alpha_amount == -500.0
    assert comparison.alpha_percent == -5.0
    assert comparison.outperformed is False


def test_build_report_contains_result_status():
    strategy = StrategyResult(
        starting_balance=10000.0,
        ending_balance=12000.0,
        net_pnl=2000.0,
        return_percent=20.0,
        total_trades=4,
    )
    benchmark = calculate_buy_and_hold([100.0, 110.0], 10000.0)
    comparison = compare_strategy_to_benchmark(strategy, benchmark)

    report = build_report(comparison)

    assert "HQE STRATEGY" in report
    assert "BUY AND HOLD" in report
    assert "HQE OUTPERFORMED buy-and-hold" in report


def test_write_summary_csv_creates_expected_file(tmp_path: Path):
    strategy = StrategyResult(
        starting_balance=10000.0,
        ending_balance=10500.0,
        net_pnl=500.0,
        return_percent=5.0,
        total_trades=3,
    )
    benchmark = calculate_buy_and_hold([100.0, 110.0], 10000.0)
    comparison = compare_strategy_to_benchmark(strategy, benchmark)

    output_path = tmp_path / "summary.csv"
    write_summary_csv(comparison, output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("strategy_ending_balance")
    assert "10500.0,500.0,5.0,3,11000.0,1000.0,10.0,-500.0,-5.0,False" in lines[1]
