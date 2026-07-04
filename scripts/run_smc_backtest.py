"""
Run SMC Backtest

Executable script for running the Hunter Quant Engine SMC strategy over
CSV historical candle data.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtesting.backtest_pipeline import BacktestPipeline
from src.historical_data.providers.csv_historical_data_provider import (
    CSVHistoricalDataProvider,
)
from src.risk.risk_manager import RiskManager
from src.risk.risk_profile import RiskProfile
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)
from src.strategy.signal_type import SignalType
from src.strategy.smc_strategy import SMCStrategy
from src.trade_planning.smc_trade_candidate_planner import (
    SMCTradeCandidatePlanner,
)


DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "nifty_5min.csv"
DEFAULT_SYMBOL = "NIFTY"
DEFAULT_TIMEFRAME = "5m"
DEFAULT_ACCOUNT_BALANCE = 10000.0
DEFAULT_RISK_PER_TRADE = 0.01
DEFAULT_REWARD_TO_RISK = 2.0

EXIT_REASON_TAKE_PROFIT = "take_profit"
EXIT_REASON_STOP_LOSS = "stop_loss"
EXIT_REASON_UNKNOWN = "unknown"

PRICE_TOLERANCE = 0.000000001

TRADE_EXPORT_COLUMNS = (
    "trade_number",
    "direction",
    "opened_at",
    "closed_at",
    "entry_price",
    "stop_loss",
    "take_profit",
    "exit_price",
    "exit_reason",
    "position_size",
    "pnl",
    "risk_multiple",
    "entry_logic",
    "stop_loss_logic",
    "take_profit_logic",
    "position_size_logic",
    "pnl_formula",
)


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
    parser.add_argument(
        "--trades-output",
        default=None,
        help="Optional CSV path for exporting completed trade details.",
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


def format_signal_type(
    signal_type: Any,
) -> str:
    """
    Format signal type for human-readable reporting.

    Args:
        signal_type: SignalType enum or enum-like/string value.

    Returns:
        Uppercase signal type text.
    """
    value = getattr(signal_type, "value", signal_type)

    return str(value).upper()


def prices_match(
    first_price: float,
    second_price: float,
) -> bool:
    """
    Return True when two prices are equal within report tolerance.

    Args:
        first_price: First price.
        second_price: Second price.

    Returns:
        True when prices match within tolerance.
    """
    return abs(first_price - second_price) <= PRICE_TOLERANCE


def infer_exit_reason(
    trade: Any,
) -> str:
    """
    Infer exit reason from completed trade prices.

    Args:
        trade: TradeResult-like object.

    Returns:
        take_profit, stop_loss, or unknown.
    """
    if prices_match(trade.exit_price, trade.take_profit):
        return EXIT_REASON_TAKE_PROFIT

    if prices_match(trade.exit_price, trade.stop_loss):
        return EXIT_REASON_STOP_LOSS

    return EXIT_REASON_UNKNOWN


def pnl_formula_for_signal(
    signal_type: Any,
) -> str:
    """
    Return PnL formula explanation for a signal type.

    Args:
        signal_type: SignalType enum or enum-like/string value.

    Returns:
        Human-readable PnL formula.
    """
    if _is_long_signal(signal_type):
        return "(Exit Price - Entry Price) * Position Size"

    if _is_short_signal(signal_type):
        return "(Entry Price - Exit Price) * Position Size"

    return "Unknown directional PnL formula"


def entry_logic_for_signal(
    signal_type: Any,
) -> tuple[str, ...]:
    """
    Return SMC trade planning explanation for a signal type.

    Args:
        signal_type: SignalType enum or enum-like/string value.

    Returns:
        Human-readable entry and stop-loss logic lines.
    """
    if _is_long_signal(signal_type):
        return (
            "Signal Logic: Bullish SMC setup was valid.",
            "Entry Zone Priority: Bullish Order Block first, Bullish FVG fallback.",
            "Entry Formula: midpoint of selected bullish entry zone.",
            "Stop Loss Formula: selected bullish entry zone low.",
        )

    if _is_short_signal(signal_type):
        return (
            "Signal Logic: Bearish SMC setup was valid.",
            "Entry Zone Priority: Bearish Order Block first, Bearish FVG fallback.",
            "Entry Formula: midpoint of selected bearish entry zone.",
            "Stop Loss Formula: selected bearish entry zone high.",
        )

    return (
        "Signal Logic: Directional SMC setup was not available.",
    )


def trade_export_logic_fields(
    signal_type: Any,
) -> dict[str, str]:
    """
    Build CSV-friendly trade logic fields.

    Args:
        signal_type: SignalType enum or enum-like/string value.

    Returns:
        Mapping of logic columns to explanations.
    """
    if _is_long_signal(signal_type):
        return {
            "entry_logic": "Bullish OB midpoint first, Bullish FVG midpoint fallback",
            "stop_loss_logic": "Selected bullish entry zone low",
            "take_profit_logic": "Fixed reward-to-risk target from RiskManager",
            "position_size_logic": "Fixed-risk sizing from RiskManager",
            "pnl_formula": pnl_formula_for_signal(signal_type),
        }

    if _is_short_signal(signal_type):
        return {
            "entry_logic": "Bearish OB midpoint first, Bearish FVG midpoint fallback",
            "stop_loss_logic": "Selected bearish entry zone high",
            "take_profit_logic": "Fixed reward-to-risk target from RiskManager",
            "position_size_logic": "Fixed-risk sizing from RiskManager",
            "pnl_formula": pnl_formula_for_signal(signal_type),
        }

    return {
        "entry_logic": "Unknown",
        "stop_loss_logic": "Unknown",
        "take_profit_logic": "Unknown",
        "position_size_logic": "Unknown",
        "pnl_formula": pnl_formula_for_signal(signal_type),
    }


def _is_long_signal(
    signal_type: Any,
) -> bool:
    value = getattr(signal_type, "value", signal_type)

    return signal_type == SignalType.LONG or str(value).lower() == "long"


def _is_short_signal(
    signal_type: Any,
) -> bool:
    value = getattr(signal_type, "value", signal_type)

    return signal_type == SignalType.SHORT or str(value).lower() == "short"


def build_trade_detail_lines(
    trade: Any,
    trade_number: int,
) -> list[str]:
    """
    Build detailed explainable report lines for one completed trade.

    Args:
        trade: TradeResult-like object.
        trade_number: One-based trade number.

    Returns:
        Report lines.
    """
    direction = format_signal_type(trade.signal_type)
    exit_reason = infer_exit_reason(trade)

    lines = [
        f"Trade #{trade_number}",
        format_metric("Direction", direction),
        format_metric("Opened At", trade.opened_at),
        format_metric("Closed At", trade.closed_at),
        format_metric("Entry Price", trade.entry_price),
        format_metric("Stop Loss", trade.stop_loss),
        format_metric("Take Profit", trade.take_profit),
        format_metric("Exit Price", trade.exit_price),
        format_metric("Exit Reason", exit_reason),
        format_metric("Position Size", trade.position_size),
        format_metric("PnL", trade.pnl),
        format_metric("Risk Multiple", trade.risk_multiple),
        "Logic",
    ]

    lines.extend(
        f"- {logic_line}"
        for logic_line in entry_logic_for_signal(trade.signal_type)
    )
    lines.extend(
        [
            "- Take Profit Formula: fixed reward-to-risk target from RiskManager.",
            "- Position Size Formula: fixed-risk sizing from RiskManager.",
            f"- PnL Formula: {pnl_formula_for_signal(trade.signal_type)}.",
        ]
    )

    return lines


def build_trade_details_section(
    trades: tuple[Any, ...],
) -> list[str]:
    """
    Build detailed explainable trade report section.

    Args:
        trades: Completed trades.

    Returns:
        Report lines.
    """
    if not trades:
        return []

    lines = [
        "------------------------------------------------------------",
        "TRADE DETAILS",
        "------------------------------------------------------------",
    ]

    for index, trade in enumerate(trades, start=1):
        if index > 1:
            lines.append("------------------------------------------------------------")

        lines.extend(
            build_trade_detail_lines(
                trade=trade,
                trade_number=index,
            )
        )

    return lines


def trade_to_export_row(
    trade: Any,
    trade_number: int,
) -> dict[str, Any]:
    """
    Convert a completed trade into a CSV export row.

    Args:
        trade: TradeResult-like object.
        trade_number: One-based trade number.

    Returns:
        CSV export row.
    """
    logic_fields = trade_export_logic_fields(trade.signal_type)

    return {
        "trade_number": trade_number,
        "direction": format_signal_type(trade.signal_type),
        "opened_at": trade.opened_at.isoformat(),
        "closed_at": trade.closed_at.isoformat(),
        "entry_price": trade.entry_price,
        "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit,
        "exit_price": trade.exit_price,
        "exit_reason": infer_exit_reason(trade),
        "position_size": trade.position_size,
        "pnl": trade.pnl,
        "risk_multiple": trade.risk_multiple,
        **logic_fields,
    }


def export_trades_to_csv(
    trades: tuple[Any, ...],
    output_path: str | Path,
) -> Path:
    """
    Export completed trades to CSV.

    Args:
        trades: Completed trade results.
        output_path: Output CSV path.

    Returns:
        Output CSV path.
    """
    csv_path = Path(output_path)
    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with csv_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=TRADE_EXPORT_COLUMNS,
        )
        writer.writeheader()

        for index, trade in enumerate(trades, start=1):
            writer.writerow(
                trade_to_export_row(
                    trade=trade,
                    trade_number=index,
                )
            )

    return csv_path


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
        ]
    )
    lines.extend(build_trade_details_section(tuple(result.trades)))
    lines.extend(
        [
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

    if args.trades_output is not None:
        exported_path = export_trades_to_csv(
            trades=tuple(result.trades),
            output_path=args.trades_output,
        )

        print(format_metric("Trades Exported", exported_path))


if __name__ == "__main__":
    main()
