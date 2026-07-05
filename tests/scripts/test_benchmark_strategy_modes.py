"""
Strategy Mode Benchmark Script Tests
"""

from pathlib import Path
import subprocess
import sys

import pytest

from scripts.benchmark_strategy_modes import (
    ModeBenchmarkResult,
    TradeCostSummary,
    benchmark_strategy_modes,
    build_argument_parser,
    build_report,
    load_trade_cost_summary,
    result_status,
    write_summary_csv,
)
from scripts.run_fyers_nifty_research import build_output_paths
from src.config.strategy_config import supported_strategy_mode_names


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.modes == list(supported_strategy_mode_names())
    assert args.output_prefix == "fyers_nifty_5m"


def test_build_argument_parser_accepts_custom_modes():
    args = build_argument_parser().parse_args(
        [
            "--modes",
            "strict",
            "relaxed",
        ]
    )

    assert args.modes == [
        "strict",
        "relaxed",
    ]


def test_load_trade_cost_summary_handles_no_trades(tmp_path: Path):
    trades_csv = tmp_path / "trades.csv"
    trades_csv.write_text(
        "pnl,total_charges,net_pnl\n",
        encoding="utf-8",
    )

    assert load_trade_cost_summary(trades_csv) == TradeCostSummary(
        gross_pnl=0.0,
        total_charges=0.0,
        net_pnl=0.0,
        total_trades=0,
    )


def test_load_trade_cost_summary_sums_trade_rows(tmp_path: Path):
    trades_csv = tmp_path / "trades.csv"
    trades_csv.write_text(
        "pnl,total_charges,net_pnl\n"
        "100.0,10.0,90.0\n"
        "-20.0,5.0,-25.0\n",
        encoding="utf-8",
    )

    assert load_trade_cost_summary(trades_csv) == TradeCostSummary(
        gross_pnl=80.0,
        total_charges=15.0,
        net_pnl=65.0,
        total_trades=2,
    )


def test_load_trade_cost_summary_rejects_missing_columns(tmp_path: Path):
    trades_csv = tmp_path / "trades.csv"
    trades_csv.write_text(
        "pnl,total_charges\n"
        "100.0,10.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required columns"):
        load_trade_cost_summary(trades_csv)


def test_result_status_formats_outperformance():
    result = ModeBenchmarkResult(
        strategy_mode="balanced",
        normalized_output_path=Path("normalized.csv"),
        trades_output_path=Path("trades.csv"),
        equity_output_path=Path("equity.csv"),
        gross_pnl=100.0,
        total_charges=10.0,
        net_pnl=90.0,
        strategy_return_percent=1.0,
        benchmark_return_percent=0.5,
        alpha_amount=50.0,
        alpha_percent=0.5,
        outperformed=True,
        total_trades=1,
    )

    assert result_status(result) == "OUTPERFORMED"


def test_build_report_includes_each_mode():
    results = (
        ModeBenchmarkResult(
            strategy_mode="strict",
            normalized_output_path=Path("strict_normalized.csv"),
            trades_output_path=Path("strict_trades.csv"),
            equity_output_path=Path("strict_equity.csv"),
            gross_pnl=0.0,
            total_charges=0.0,
            net_pnl=0.0,
            strategy_return_percent=0.0,
            benchmark_return_percent=5.0,
            alpha_amount=-500.0,
            alpha_percent=-5.0,
            outperformed=False,
            total_trades=0,
        ),
        ModeBenchmarkResult(
            strategy_mode="relaxed",
            normalized_output_path=Path("relaxed_normalized.csv"),
            trades_output_path=Path("relaxed_trades.csv"),
            equity_output_path=Path("relaxed_equity.csv"),
            gross_pnl=100.0,
            total_charges=10.0,
            net_pnl=90.0,
            strategy_return_percent=0.9,
            benchmark_return_percent=0.5,
            alpha_amount=40.0,
            alpha_percent=0.4,
            outperformed=True,
            total_trades=1,
        ),
    )

    report = build_report(results)

    assert "Hunter Quant Engine - Strategy Mode Benchmark" in report
    assert "strict | 0 | 0.00 | 0.00 | 0.00" in report
    assert "relaxed | 1 | 100.00 | 10.00 | 90.00" in report
    assert "HQE UNDERPERFORMED buy-and-hold" in report
    assert "HQE OUTPERFORMED buy-and-hold" in report


def test_write_summary_csv_creates_expected_file(tmp_path: Path):
    output_path = tmp_path / "summary.csv"
    result = ModeBenchmarkResult(
        strategy_mode="balanced",
        normalized_output_path=Path("balanced_normalized.csv"),
        trades_output_path=Path("balanced_trades.csv"),
        equity_output_path=Path("balanced_equity.csv"),
        gross_pnl=100.0,
        total_charges=10.0,
        net_pnl=90.0,
        strategy_return_percent=0.9,
        benchmark_return_percent=1.2,
        alpha_amount=-30.0,
        alpha_percent=-0.3,
        outperformed=False,
        total_trades=1,
    )

    write_summary_csv((result,), output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("strategy_mode,total_trades,gross_pnl")
    assert "balanced,1,100.0,10.0,90.0" in lines[1]


def test_benchmark_strategy_modes_runs_all_modes_and_creates_outputs(tmp_path: Path):
    input_path = tmp_path / "raw.csv"
    output_dir = tmp_path / "processed"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,100.0,1000",
                "2026-01-01T09:20:00,100.0,106.0,99.0,105.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    results = benchmark_strategy_modes(
        input_path=input_path,
        output_dir=output_dir,
        output_prefix="mode_test",
        symbol="TEST",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        modes=("strict", "balanced", "relaxed"),
    )

    assert tuple(result.strategy_mode for result in results) == (
        "strict",
        "balanced",
        "relaxed",
    )

    for result in results:
        output_paths = build_output_paths(
            output_dir=output_dir,
            output_prefix=f"mode_test_{result.strategy_mode}",
        )

        assert result.normalized_output_path == output_paths.normalized_output_path
        assert result.trades_output_path == output_paths.trades_output_path
        assert result.equity_output_path == output_paths.equity_output_path
        assert result.normalized_output_path.exists()
        assert result.trades_output_path.exists()
        assert result.equity_output_path.exists()
        assert result.total_trades == 0
        assert result.net_pnl == 0.0
        assert result.strategy_return_percent == 0.0
        assert result.benchmark_return_percent == 5.0
        assert result.alpha_percent == -5.0
        assert result.outperformed is False


def test_benchmark_script_can_run_as_direct_file():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_strategy_modes.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Benchmark strict, balanced, and relaxed HQE strategy modes." in (
        completed.stdout
    )

def test_build_report_includes_runtime_metrics():
    result = ModeBenchmarkResult(
        strategy_mode="strict",
        normalized_output_path=Path("strict_normalized.csv"),
        trades_output_path=Path("strict_trades.csv"),
        equity_output_path=Path("strict_equity.csv"),
        gross_pnl=100.0,
        total_charges=10.0,
        net_pnl=90.0,
        strategy_return_percent=0.9,
        benchmark_return_percent=1.2,
        alpha_amount=-30.0,
        alpha_percent=-0.3,
        outperformed=False,
        total_trades=1,
        runtime_seconds=12.345,
    )

    report = build_report((result,))

    assert "Runtime Seconds" in report
    assert "strict | 1 | 100.00 | 10.00 | 90.00" in report
    assert "12.35" in report
    assert "Total Runtime Seconds: 12.35" in report


def test_write_summary_csv_includes_runtime_seconds(tmp_path: Path):
    output_path = tmp_path / "summary.csv"
    result = ModeBenchmarkResult(
        strategy_mode="balanced",
        normalized_output_path=Path("balanced_normalized.csv"),
        trades_output_path=Path("balanced_trades.csv"),
        equity_output_path=Path("balanced_equity.csv"),
        gross_pnl=100.0,
        total_charges=10.0,
        net_pnl=90.0,
        strategy_return_percent=0.9,
        benchmark_return_percent=1.2,
        alpha_amount=-30.0,
        alpha_percent=-0.3,
        outperformed=False,
        total_trades=1,
        runtime_seconds=7.5,
    )

    write_summary_csv((result,), output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].endswith(",runtime_seconds")
    assert lines[1].endswith(",7.5")


def test_benchmark_strategy_modes_emits_progress_and_runtime(tmp_path: Path):
    input_path = tmp_path / "raw.csv"
    output_dir = tmp_path / "processed"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,100.0,1000",
                "2026-01-01T09:20:00,100.0,106.0,99.0,105.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    progress_messages = []
    clock_values = iter([10.0, 11.5])

    results = benchmark_strategy_modes(
        input_path=input_path,
        output_dir=output_dir,
        output_prefix="mode_test",
        symbol="TEST",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        modes=("strict",),
        progress_callback=progress_messages.append,
        clock=lambda: next(clock_values),
    )

    assert len(results) == 1
    assert results[0].runtime_seconds == 1.5
    assert progress_messages == [
        "Running mode: strict",
        "Finished mode: strict in 1.50 seconds",
    ]
