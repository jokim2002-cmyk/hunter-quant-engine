"""
Run SMC Backtest Script Tests
"""

from pathlib import Path
from types import SimpleNamespace

from scripts.run_smc_backtest import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_CSV_PATH,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    build_argument_parser,
    build_report,
    build_risk_profile,
)


def test_build_argument_parser_uses_expected_defaults():
    args = build_argument_parser().parse_args([])

    assert args.csv == str(DEFAULT_CSV_PATH)
    assert args.symbol == DEFAULT_SYMBOL
    assert args.timeframe == DEFAULT_TIMEFRAME
    assert args.account_balance == DEFAULT_ACCOUNT_BALANCE
    assert args.risk_per_trade == DEFAULT_RISK_PER_TRADE
    assert args.reward_to_risk == DEFAULT_REWARD_TO_RISK


def test_build_argument_parser_accepts_custom_values():
    args = build_argument_parser().parse_args(
        [
            "--csv",
            "data/raw/custom.csv",
            "--symbol",
            "EURUSD",
            "--timeframe",
            "1H",
            "--account-balance",
            "25000",
            "--risk-per-trade",
            "0.02",
            "--reward-to-risk",
            "3.0",
        ]
    )

    assert args.csv == "data/raw/custom.csv"
    assert args.symbol == "EURUSD"
    assert args.timeframe == "1H"
    assert args.account_balance == 25000.0
    assert args.risk_per_trade == 0.02
    assert args.reward_to_risk == 3.0


def test_build_risk_profile_creates_expected_profile():
    risk_profile = build_risk_profile(
        account_balance=10000.0,
        risk_per_trade=0.01,
        reward_to_risk=2.0,
    )

    assert risk_profile.account_balance == 10000.0
    assert risk_profile.risk_per_trade == 0.01
    assert risk_profile.reward_to_risk == 2.0


def test_build_report_includes_required_summary_metrics():
    result = SimpleNamespace(
        trades=(),
        performance_summary=SimpleNamespace(
            total_trades=0,
            total_pnl=0.0,
        ),
    )

    report = build_report(
        result=result,
        csv_path=Path("data/raw/nifty_5min.csv"),
        symbol="NIFTY",
        timeframe="5m",
    )

    assert "Hunter Quant Engine - SMC Backtest Result" in report
    assert "CSV: data\\raw\\nifty_5min.csv" in report or "CSV: data/raw/nifty_5min.csv" in report
    assert "Symbol: NIFTY" in report
    assert "Timeframe: 5m" in report
    assert "Total Trades: 0" in report
    assert "Total PnL: 0.0" in report
    assert "Closed Trades: 0" in report


def test_build_report_includes_optional_summary_metrics_when_available():
    result = SimpleNamespace(
        trades=(object(),),
        performance_summary=SimpleNamespace(
            total_trades=1,
            total_pnl=100.0,
            winning_trades=1,
            losing_trades=0,
            win_rate=1.0,
            average_pnl=100.0,
            max_drawdown=0.0,
            profit_factor=999.0,
            average_risk_multiple=2.0,
        ),
    )

    report = build_report(
        result=result,
        csv_path=Path("data/raw/nifty_5min.csv"),
        symbol="NIFTY",
        timeframe="5m",
    )

    assert "Winning Trades: 1" in report
    assert "Losing Trades: 0" in report
    assert "Win Rate: 1.0" in report
    assert "Average PnL: 100.0" in report
    assert "Max Drawdown: 0.0" in report
    assert "Profit Factor: 999.0" in report
    assert "Average R Multiple: 2.0" in report
