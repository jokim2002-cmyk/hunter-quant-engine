"""
Run SMC Backtest

Executable script for running the Hunter Quant Engine SMC strategy over
CSV historical candle data.
"""

import argparse
from pathlib import Path
from typing import Any

from src.backtesting.backtest_pipeline import BacktestPipeline
from src.historical_data.providers.csv_historical_data_provider import (
    CSVHistoricalDataProvider,
)
from src.risk.risk_manager import RiskManager
from src.risk.risk_profile import RiskProfile
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)
from src.strategy.smc_strategy import SMCStrategy
from src.trade_planning.smc_trade_candidate_planner import (
    SMCTradeCandidatePlanner,
)


DEFAULT_CSV_PATH = Path("data/raw/nifty_5min.csv")
DEFAULT_SYMBOL = "NIFTY"
DEFAULT_TIMEFRAME = "5m"
DEFAULT_ACCOUNT_BALANCE = 10000.0
DEFAULT_RISK_PER_TRADE = 0.01
DEFAULT_REWARD_TO_RISK = 2.0


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Run HQE SMC backtest over CSV candle data.",
    )

    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV_PATH),
        help="Path to CSV file with datetime, open, high, low, close, volume columns.",
    )
    parser.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
        help="Market symbol used in StrategyContext.",
    )
    parser.add_argument(
        "--timeframe",
        default=DEFAULT_TIMEFRAME,
        help="Market timeframe used in StrategyContext.",
    )
    parser.add_argument(
        "--account-balance",
        type=float,
        default=DEFAULT_ACCOUNT_BALANCE,
        help="Account balance used for risk calculations.",
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=DEFAULT_RISK_PER_TRADE,
        help="Risk per trade as decimal. Example: 0.01 means 1%%.",
    )
    parser.add_argument(
        "--reward-to-risk",
        type=float,
        default=DEFAULT_REWARD_TO_RISK,
        help="Reward-to-risk multiple used for take-profit planning.",
    )

    return parser


def build_risk_profile(
    account_balance: float,
    risk_per_trade: float,
    reward_to_risk: float,
) -> RiskProfile:
    """
    Build immutable risk profile for the backtest.

    Args:
        account_balance: Backtest account balance.
        risk_per_trade: Risk per trade as decimal.
        reward_to_risk: Reward-to-risk multiple.

    Returns:
        Immutable RiskProfile.
    """
    return RiskProfile(
        account_balance=account_balance,
        risk_per_trade=risk_per_trade,
        reward_to_risk=reward_to_risk,
    )


def build_pipeline(
    csv_path: str | Path,
    symbol: str,
    timeframe: str,
    risk_profile: RiskProfile,
) -> BacktestPipeline:
    """
    Build the full HQE SMC backtest pipeline.

    Args:
        csv_path: CSV historical data path.
        symbol: Market symbol.
        timeframe: Market timeframe.
        risk_profile: Immutable risk profile.

    Returns:
        Configured BacktestPipeline.
    """
    return BacktestPipeline(
        historical_data_provider=CSVHistoricalDataProvider(csv_path),
        strategy=SMCStrategy(),
        trade_candidate_planner=SMCTradeCandidatePlanner(),
        risk_manager=RiskManager(),
        risk_profile=risk_profile,
        symbol=symbol,
        timeframe=timeframe,
        strategy_context_factory=DefaultStrategyContextFactory(),
    )


def format_metric(
    label: str,
    value: Any,
) -> str:
    """
    Format a metric line for console output.

    Args:
        label: Metric label.
        value: Metric value.

    Returns:
        Formatted metric line.
    """
    return f"{label}: {value}"


def optional_metric(
    summary: Any,
    attribute_name: str,
    label: str,
) -> str | None:
    """
    Format an optional performance summary metric when it exists.

    Args:
        summary: Performance summary object.
        attribute_name: Attribute to inspect.
        label: Metric label.

    Returns:
        Formatted metric line when attribute exists, otherwise None.
    """
    if not hasattr(summary, attribute_name):
        return None

    return format_metric(label, getattr(summary, attribute_name))


def build_report(
    result: Any,
    csv_path: str | Path,
    symbol: str,
    timeframe: str,
) -> str:
    """
    Build a human-readable backtest report.

    Args:
        result: BacktestResult.
        csv_path: CSV path used.
        symbol: Market symbol.
        timeframe: Market timeframe.

    Returns:
        Multiline report string.
    """
    summary = result.performance_summary

    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - SMC Backtest Result",
        "============================================================",
        format_metric("CSV", Path(csv_path)),
        format_metric("Symbol", symbol),
        format_metric("Timeframe", timeframe),
        "------------------------------------------------------------",
        format_metric("Total Trades", summary.total_trades),
        format_metric("Total PnL", summary.total_pnl),
    ]

    optional_metrics = (
        ("winning_trades", "Winning Trades"),
        ("losing_trades", "Losing Trades"),
        ("win_rate", "Win Rate"),
        ("average_pnl", "Average PnL"),
        ("max_drawdown", "Max Drawdown"),
        ("profit_factor", "Profit Factor"),
        ("average_risk_multiple", "Average R Multiple"),
    )

    for attribute_name, label in optional_metrics:
        metric = optional_metric(
            summary=summary,
            attribute_name=attribute_name,
            label=label,
        )

        if metric is not None:
            lines.append(metric)

    lines.extend(
        [
            "------------------------------------------------------------",
            format_metric("Closed Trades", len(result.trades)),
            "============================================================",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """
    Run the SMC backtest and print the result report.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    csv_path = Path(args.csv)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}. "
            "Provide a valid path with --csv."
        )

    risk_profile = build_risk_profile(
        account_balance=args.account_balance,
        risk_per_trade=args.risk_per_trade,
        reward_to_risk=args.reward_to_risk,
    )
    pipeline = build_pipeline(
        csv_path=csv_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        risk_profile=risk_profile,
    )

    result = pipeline.run()

    print(
        build_report(
            result=result,
            csv_path=csv_path,
            symbol=args.symbol,
            timeframe=args.timeframe,
        )
    )


if __name__ == "__main__":
    main()
