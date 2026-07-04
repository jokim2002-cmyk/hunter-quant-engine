"""
Run SMC Backtest Script Tests
"""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from scripts.run_smc_backtest import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_CSV_PATH,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    EXIT_REASON_STOP_LOSS,
    EXIT_REASON_TAKE_PROFIT,
    EXIT_REASON_UNKNOWN,
    build_argument_parser,
    build_report,
    build_risk_profile,
    infer_exit_reason,
)
from src.strategy.signal_type import SignalType


def _completed_trade(
    signal_type=SignalType.LONG,
    entry_price=100.0,
    exit_price=108.0,
    stop_loss=96.0,
    take_profit=108.0,
    position_size=50.0,
    pnl=400.0,
    risk_multiple=2.0,
):
    return SimpleNamespace(
        signal_type=signal_type,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=position_size,
        pnl=pnl,
        risk_multiple=risk_multiple,
        opened_at=datetime(2026, 1, 1, 9, 30),
        closed_at=datetime(2026, 1, 1, 9, 45),
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
    assert (
        "CSV: data\\raw\\nifty_5min.csv" in report
        or "CSV: data/raw/nifty_5min.csv" in report
    )
    assert "Symbol: NIFTY" in report
    assert "Timeframe: 5m" in report
    assert "Total Trades: 0" in report
    assert "Total PnL: 0.0" in report
    assert "Closed Trades: 0" in report
    assert "TRADE DETAILS" not in report


def test_build_report_includes_optional_summary_metrics_when_available():
    result = SimpleNamespace(
        trades=(
            _completed_trade(
                pnl=100.0,
                risk_multiple=2.0,
            ),
        ),
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


def test_infer_exit_reason_returns_take_profit_when_exit_matches_take_profit():
    trade = SimpleNamespace(
        exit_price=108.0,
        take_profit=108.0,
        stop_loss=96.0,
    )

    assert infer_exit_reason(trade) == EXIT_REASON_TAKE_PROFIT


def test_infer_exit_reason_returns_stop_loss_when_exit_matches_stop_loss():
    trade = SimpleNamespace(
        exit_price=96.0,
        take_profit=108.0,
        stop_loss=96.0,
    )

    assert infer_exit_reason(trade) == EXIT_REASON_STOP_LOSS


def test_infer_exit_reason_returns_unknown_when_exit_matches_no_level():
    trade = SimpleNamespace(
        exit_price=101.0,
        take_profit=108.0,
        stop_loss=96.0,
    )

    assert infer_exit_reason(trade) == EXIT_REASON_UNKNOWN


def test_build_report_includes_explainable_long_trade_details():
    trade = _completed_trade(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        exit_price=108.0,
        stop_loss=96.0,
        take_profit=108.0,
        position_size=50.0,
        pnl=400.0,
        risk_multiple=2.0,
    )
    result = SimpleNamespace(
        trades=(trade,),
        performance_summary=SimpleNamespace(
            total_trades=1,
            total_pnl=400.0,
        ),
    )

    report = build_report(
        result=result,
        csv_path=Path("data/raw/demo_smc_5min.csv"),
        symbol="DEMO",
        timeframe="5m",
    )

    assert "TRADE DETAILS" in report
    assert "Trade #1" in report
    assert "Direction: LONG" in report
    assert "Opened At: 2026-01-01 09:30:00" in report
    assert "Closed At: 2026-01-01 09:45:00" in report
    assert "Entry Price: 100.0" in report
    assert "Stop Loss: 96.0" in report
    assert "Take Profit: 108.0" in report
    assert "Exit Price: 108.0" in report
    assert "Exit Reason: take_profit" in report
    assert "Position Size: 50.0" in report
    assert "PnL: 400.0" in report
    assert "Risk Multiple: 2.0" in report
    assert "Signal Logic: Bullish SMC setup was valid." in report
    assert "Entry Zone Priority: Bullish Order Block first, Bullish FVG fallback." in report
    assert "Entry Formula: midpoint of selected bullish entry zone." in report
    assert "Stop Loss Formula: selected bullish entry zone low." in report
    assert "Take Profit Formula: fixed reward-to-risk target from RiskManager." in report
    assert "Position Size Formula: fixed-risk sizing from RiskManager." in report
    assert "PnL Formula: (Exit Price - Entry Price) * Position Size." in report


def test_build_report_includes_explainable_short_trade_details():
    trade = _completed_trade(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        exit_price=92.0,
        stop_loss=104.0,
        take_profit=92.0,
        position_size=50.0,
        pnl=400.0,
        risk_multiple=2.0,
    )
    result = SimpleNamespace(
        trades=(trade,),
        performance_summary=SimpleNamespace(
            total_trades=1,
            total_pnl=400.0,
        ),
    )

    report = build_report(
        result=result,
        csv_path=Path("data/raw/demo_smc_5min.csv"),
        symbol="DEMO",
        timeframe="5m",
    )

    assert "Direction: SHORT" in report
    assert "Exit Reason: take_profit" in report
    assert "Signal Logic: Bearish SMC setup was valid." in report
    assert "Entry Zone Priority: Bearish Order Block first, Bearish FVG fallback." in report
    assert "Entry Formula: midpoint of selected bearish entry zone." in report
    assert "Stop Loss Formula: selected bearish entry zone high." in report
    assert "PnL Formula: (Entry Price - Exit Price) * Position Size." in report
