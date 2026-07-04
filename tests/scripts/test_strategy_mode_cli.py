"""
Strategy Mode CLI Tests
"""

from scripts import diagnose_smc_backtest
from scripts import run_fyers_nifty_research
from scripts import run_smc_backtest
from scripts import run_smc_research_workflow
from src.config.strategy_config import (
    BALANCED_SMC_STRATEGY_CONFIG,
    RELAXED_SMC_STRATEGY_CONFIG,
    STRICT_SMC_STRATEGY_CONFIG,
)


def test_smc_backtest_parser_uses_balanced_strategy_mode_by_default():
    args = run_smc_backtest.build_argument_parser().parse_args([])

    assert args.strategy_mode == BALANCED_SMC_STRATEGY_CONFIG.mode.value


def test_smc_backtest_parser_accepts_strategy_mode():
    args = run_smc_backtest.build_argument_parser().parse_args(
        [
            "--strategy-mode",
            "strict",
        ]
    )

    assert args.strategy_mode == STRICT_SMC_STRATEGY_CONFIG.mode.value


def test_diagnose_parser_accepts_strategy_mode():
    args = diagnose_smc_backtest.build_argument_parser().parse_args(
        [
            "--strategy-mode",
            "relaxed",
        ]
    )

    assert args.strategy_mode == RELAXED_SMC_STRATEGY_CONFIG.mode.value


def test_research_workflow_parser_accepts_strategy_mode():
    args = run_smc_research_workflow.build_argument_parser().parse_args(
        [
            "--strategy-mode",
            "strict",
        ]
    )

    assert args.strategy_mode == STRICT_SMC_STRATEGY_CONFIG.mode.value


def test_fyers_runner_parser_accepts_strategy_mode():
    args = run_fyers_nifty_research.build_argument_parser().parse_args(
        [
            "--strategy-mode",
            "relaxed",
        ]
    )

    assert args.strategy_mode == RELAXED_SMC_STRATEGY_CONFIG.mode.value


def test_diagnose_summary_tracks_strategy_mode(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text(
        "datetime,open,high,low,close,volume\n",
        encoding="utf-8",
    )

    summary = diagnose_smc_backtest.diagnose(
        csv_path=csv_path,
        symbol="TEST",
        timeframe="1m",
        risk_profile=diagnose_smc_backtest.build_risk_profile(
            account_balance=10000.0,
            risk_per_trade=0.01,
            reward_to_risk=2.0,
        ),
        strategy_mode="relaxed",
    )

    assert summary.strategy_mode == "relaxed"
    assert "Strategy Mode: relaxed" in diagnose_smc_backtest.build_report(summary)


def test_research_workflow_summary_tracks_strategy_mode(tmp_path):
    input_path = tmp_path / "raw.csv"
    normalized_output_path = tmp_path / "processed" / "normalized.csv"
    trades_output_path = tmp_path / "processed" / "trades.csv"
    equity_output_path = tmp_path / "processed" / "equity_curve.csv"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
                "2026-01-01T09:20:00,102.0,106.0,101.0,104.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_smc_research_workflow.run_workflow(
        input_path=input_path,
        normalized_output_path=normalized_output_path,
        trades_output_path=trades_output_path,
        equity_output_path=equity_output_path,
        symbol="TEST",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        strategy_mode="strict",
    )

    assert summary.strategy_mode == "strict"
    assert "Strategy Mode: strict" in (
        run_smc_research_workflow.build_workflow_summary_report(summary)
    )


def test_fyers_runner_summary_tracks_strategy_mode(tmp_path):
    input_path = tmp_path / "fyers_raw.csv"
    output_dir = tmp_path / "processed"

    input_path.write_text(
        "\n".join(
            [
                "datetime,open,high,low,close,volume",
                "2026-01-01T09:15:00,100.0,105.0,95.0,102.0,1000",
                "2026-01-01T09:20:00,102.0,106.0,101.0,104.0,1000",
            ]
        ),
        encoding="utf-8",
    )

    summary = run_fyers_nifty_research.run_fyers_nifty_research(
        input_path=input_path,
        output_dir=output_dir,
        output_prefix="fyers_test",
        symbol="NIFTY",
        timeframe="5m",
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
        strategy_mode="relaxed",
    )

    assert summary.strategy_mode == "relaxed"
