"""
Diagnose SMC Backtest Script Tests
"""

from pathlib import Path

from scripts.diagnose_smc_backtest import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_CSV_PATH,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    DiagnosticSummary,
    build_argument_parser,
    build_report,
    build_risk_profile,
    diagnose,
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


def test_build_report_includes_all_required_sections():
    summary = DiagnosticSummary(
        csv_path=Path("data/raw/nifty_5min.csv"),
        symbol="NIFTY",
        timeframe="5m",
        candles_loaded=10,
        market_structure_points=1,
        bos_events=2,
        choch_events=3,
        liquidity_points=4,
        equal_high_points=5,
        equal_low_points=6,
        liquidity_clusters=7,
        liquidity_sweeps=8,
        fair_value_gaps=9,
        order_blocks=10,
        long_signals=11,
        short_signals=12,
        neutral_signals=13,
        trade_candidates=14,
        trade_plans_before_deduplication=15,
        duplicate_trade_plans_removed=2,
        trade_plans_after_deduplication=13,
        closed_trades=16,
        total_pnl=100.0,
    )

    report = build_report(summary)

    assert "Hunter Quant Engine - SMC Diagnostic Report" in report
    assert "DATA" in report
    assert "FINAL CONTEXT DETECTIONS" in report
    assert "WALK-FORWARD STRATEGY" in report
    assert "EXECUTION" in report
    assert "Candles Loaded: 10" in report
    assert "BOS Events: 2" in report
    assert "Long Signals: 11" in report
    assert "Trade Candidates: 14" in report
    assert "Trade Plans Before De-duplication: 15" in report
    assert "Duplicate Trade Plans Removed: 2" in report
    assert "Trade Plans After De-duplication: 13" in report
    assert "Closed Trades: 16" in report
    assert "Total PnL: 100.0" in report


def test_diagnose_returns_zero_metrics_for_empty_csv(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text(
        "datetime,open,high,low,close,volume\n",
        encoding="utf-8",
    )

    summary = diagnose(
        csv_path=csv_path,
        symbol="TEST",
        timeframe="1m",
        risk_profile=build_risk_profile(
            account_balance=10000.0,
            risk_per_trade=0.01,
            reward_to_risk=2.0,
        ),
    )

    assert summary.csv_path == csv_path
    assert summary.symbol == "TEST"
    assert summary.timeframe == "1m"
    assert summary.candles_loaded == 0
    assert summary.market_structure_points == 0
    assert summary.bos_events == 0
    assert summary.choch_events == 0
    assert summary.liquidity_points == 0
    assert summary.equal_high_points == 0
    assert summary.equal_low_points == 0
    assert summary.liquidity_clusters == 0
    assert summary.liquidity_sweeps == 0
    assert summary.fair_value_gaps == 0
    assert summary.order_blocks == 0
    assert summary.long_signals == 0
    assert summary.short_signals == 0
    assert summary.neutral_signals == 0
    assert summary.trade_candidates == 0
    assert summary.trade_plans_before_deduplication == 0
    assert summary.duplicate_trade_plans_removed == 0
    assert summary.trade_plans_after_deduplication == 0
    assert summary.closed_trades == 0
    assert summary.total_pnl == 0.0
