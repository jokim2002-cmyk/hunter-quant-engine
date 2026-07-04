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
from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.costs.transaction_cost_profile import TransactionCostProfile
from src.costs.transaction_cost_profile_preset import (
    COST_PROFILE_CUSTOM,
    build_transaction_cost_profile_from_name,
    supported_transaction_cost_profile_names,
)
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

DEFAULT_BROKERAGE_PER_ORDER = 0.0
DEFAULT_STT_RATE = 0.0
DEFAULT_EXCHANGE_TRANSACTION_CHARGE_RATE = 0.0
DEFAULT_SEBI_CHARGE_RATE = 0.0
DEFAULT_STAMP_DUTY_RATE = 0.0
DEFAULT_GST_RATE = 0.0
DEFAULT_COST_PROFILE = COST_PROFILE_CUSTOM

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
    "brokerage",
    "stt",
    "exchange_transaction_charge",
    "sebi_charge",
    "stamp_duty",
    "gst",
    "total_charges",
    "net_pnl",
    "risk_multiple",
    "entry_logic",
    "stop_loss_logic",
    "take_profit_logic",
    "position_size_logic",
    "pnl_formula",
)

EQUITY_CURVE_EXPORT_COLUMNS = (
    "trade_number",
    "opened_at",
    "closed_at",
    "direction",
    "starting_balance",
    "pnl",
    "brokerage",
    "stt",
    "exchange_transaction_charge",
    "sebi_charge",
    "stamp_duty",
    "gst",
    "total_charges",
    "net_pnl",
    "ending_balance",
    "running_peak",
    "drawdown",
    "drawdown_percent",
    "risk_multiple",
    "exit_reason",
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
        "--cost-profile",
        default=DEFAULT_COST_PROFILE,
        choices=supported_transaction_cost_profile_names(),
        help="Named broker/segment cost profile. Use custom for manual rates.",
    )
    parser.add_argument(
        "--brokerage-per-order",
        type=float,
        default=DEFAULT_BROKERAGE_PER_ORDER,
        help="Brokerage charged per order. Round trip applies it twice.",
    )
    parser.add_argument(
        "--stt-rate",
        type=float,
        default=DEFAULT_STT_RATE,
        help="STT/CTT rate as decimal applied on exit turnover.",
    )
    parser.add_argument(
        "--exchange-transaction-charge-rate",
        type=float,
        default=DEFAULT_EXCHANGE_TRANSACTION_CHARGE_RATE,
        help="Exchange transaction charge rate as decimal on total turnover.",
    )
    parser.add_argument(
        "--sebi-charge-rate",
        type=float,
        default=DEFAULT_SEBI_CHARGE_RATE,
        help="SEBI charge rate as decimal on total turnover.",
    )
    parser.add_argument(
        "--stamp-duty-rate",
        type=float,
        default=DEFAULT_STAMP_DUTY_RATE,
        help="Stamp duty rate as decimal on entry turnover.",
    )
    parser.add_argument(
        "--gst-rate",
        type=float,
        default=DEFAULT_GST_RATE,
        help="GST rate as decimal on brokerage plus exchange and SEBI charges.",
    )
    parser.add_argument(
        "--trades-output",
        default=None,
        help="Optional CSV path for exporting completed trade details.",
    )
    parser.add_argument(
        "--equity-output",
        default=None,
        help="Optional CSV path for exporting trade-by-trade equity curve.",
    )

    return parser


def build_risk_profile(
    account_balance: float,
    risk_per_trade: float,
    reward_to_risk: float,
) -> RiskProfile:
    """
    Build immutable risk profile for the backtest.
    """
    return RiskProfile(
        account_balance=account_balance,
        risk_per_trade=risk_per_trade,
        reward_to_risk=reward_to_risk,
    )


def build_transaction_cost_profile(
    brokerage_per_order: float,
    stt_rate: float,
    exchange_transaction_charge_rate: float,
    sebi_charge_rate: float,
    stamp_duty_rate: float,
    gst_rate: float,
    cost_profile: str = DEFAULT_COST_PROFILE,
) -> TransactionCostProfile:
    """
    Build immutable transaction cost profile.
    """
    if cost_profile != COST_PROFILE_CUSTOM:
        return build_transaction_cost_profile_from_name(cost_profile)

    return TransactionCostProfile(
        brokerage_per_order=brokerage_per_order,
        stt_rate=stt_rate,
        exchange_transaction_charge_rate=exchange_transaction_charge_rate,
        sebi_charge_rate=sebi_charge_rate,
        stamp_duty_rate=stamp_duty_rate,
        gst_rate=gst_rate,
    )


def build_transaction_cost_calculator(
    transaction_cost_profile: TransactionCostProfile,
) -> TransactionCostCalculator:
    """
    Build transaction cost calculator.
    """
    return TransactionCostCalculator(transaction_cost_profile)


def build_pipeline(
    csv_path: str | Path,
    symbol: str,
    timeframe: str,
    risk_profile: RiskProfile,
) -> BacktestPipeline:
    """
    Build the full HQE SMC backtest pipeline.
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


def _cost_calculator_or_default(
    transaction_cost_calculator: TransactionCostCalculator | None,
) -> TransactionCostCalculator:
    if transaction_cost_calculator is not None:
        return transaction_cost_calculator

    return TransactionCostCalculator()


def total_transaction_charges(
    trades: tuple[Any, ...],
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> float:
    """
    Calculate total charges for completed trades.
    """
    calculator = _cost_calculator_or_default(transaction_cost_calculator)

    return sum(
        calculator.calculate(trade).total_charges
        for trade in trades
    )


def net_total_pnl(
    gross_total_pnl: float,
    trades: tuple[Any, ...],
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> float:
    """
    Calculate net total PnL after all charges.
    """
    return gross_total_pnl - total_transaction_charges(
        trades=trades,
        transaction_cost_calculator=transaction_cost_calculator,
    )


def format_metric(
    label: str,
    value: Any,
) -> str:
    """
    Format a metric line for console output.
    """
    return f"{label}: {value}"


def optional_metric(
    summary: Any,
    attribute_name: str,
    label: str,
) -> str | None:
    """
    Format an optional performance summary metric when it exists.
    """
    if not hasattr(summary, attribute_name):
        return None

    return format_metric(label, getattr(summary, attribute_name))


def format_signal_type(
    signal_type: Any,
) -> str:
    """
    Format signal type for human-readable reporting.
    """
    value = getattr(signal_type, "value", signal_type)

    return str(value).upper()


def prices_match(
    first_price: float,
    second_price: float,
) -> bool:
    """
    Return True when two prices are equal within report tolerance.
    """
    return abs(first_price - second_price) <= PRICE_TOLERANCE


def infer_exit_reason(
    trade: Any,
) -> str:
    """
    Infer exit reason from completed trade prices.
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
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> list[str]:
    """
    Build detailed explainable report lines for one completed trade.
    """
    calculator = _cost_calculator_or_default(transaction_cost_calculator)
    cost_breakdown = calculator.calculate(trade)
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
        format_metric("Total Charges", cost_breakdown.total_charges),
        format_metric("Net PnL", cost_breakdown.net_pnl),
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
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> list[str]:
    """
    Build detailed explainable trade report section.
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
                transaction_cost_calculator=transaction_cost_calculator,
            )
        )

    return lines


def trade_to_export_row(
    trade: Any,
    trade_number: int,
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> dict[str, Any]:
    """
    Convert a completed trade into a CSV export row.
    """
    calculator = _cost_calculator_or_default(transaction_cost_calculator)
    cost_breakdown = calculator.calculate(trade)
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
        "brokerage": cost_breakdown.brokerage,
        "stt": cost_breakdown.stt,
        "exchange_transaction_charge": cost_breakdown.exchange_transaction_charge,
        "sebi_charge": cost_breakdown.sebi_charge,
        "stamp_duty": cost_breakdown.stamp_duty,
        "gst": cost_breakdown.gst,
        "total_charges": cost_breakdown.total_charges,
        "net_pnl": cost_breakdown.net_pnl,
        "risk_multiple": trade.risk_multiple,
        **logic_fields,
    }


def export_trades_to_csv(
    trades: tuple[Any, ...],
    output_path: str | Path,
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> Path:
    """
    Export completed trades to CSV.
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
                    transaction_cost_calculator=transaction_cost_calculator,
                )
            )

    return csv_path


def calculate_drawdown(
    ending_balance: float,
    running_peak: float,
) -> tuple[float, float]:
    """
    Calculate drawdown amount and percentage.
    """
    drawdown = max(running_peak - ending_balance, 0.0)

    if running_peak <= 0:
        return drawdown, 0.0

    return drawdown, drawdown / running_peak


def trade_to_equity_curve_row(
    trade: Any,
    trade_number: int,
    starting_balance: float,
    current_peak: float,
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> dict[str, Any]:
    """
    Convert a completed trade into an equity curve CSV row.
    """
    calculator = _cost_calculator_or_default(transaction_cost_calculator)
    cost_breakdown = calculator.calculate(trade)
    ending_balance = starting_balance + cost_breakdown.net_pnl
    running_peak = max(current_peak, ending_balance)
    drawdown, drawdown_percent = calculate_drawdown(
        ending_balance=ending_balance,
        running_peak=running_peak,
    )

    return {
        "trade_number": trade_number,
        "opened_at": trade.opened_at.isoformat(),
        "closed_at": trade.closed_at.isoformat(),
        "direction": format_signal_type(trade.signal_type),
        "starting_balance": starting_balance,
        "pnl": trade.pnl,
        "brokerage": cost_breakdown.brokerage,
        "stt": cost_breakdown.stt,
        "exchange_transaction_charge": cost_breakdown.exchange_transaction_charge,
        "sebi_charge": cost_breakdown.sebi_charge,
        "stamp_duty": cost_breakdown.stamp_duty,
        "gst": cost_breakdown.gst,
        "total_charges": cost_breakdown.total_charges,
        "net_pnl": cost_breakdown.net_pnl,
        "ending_balance": ending_balance,
        "running_peak": running_peak,
        "drawdown": drawdown,
        "drawdown_percent": drawdown_percent,
        "risk_multiple": trade.risk_multiple,
        "exit_reason": infer_exit_reason(trade),
    }


def export_equity_curve_to_csv(
    trades: tuple[Any, ...],
    output_path: str | Path,
    starting_balance: float,
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> Path:
    """
    Export trade-by-trade equity curve to CSV.
    """
    csv_path = Path(output_path)
    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    running_balance = starting_balance
    running_peak = starting_balance

    with csv_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=EQUITY_CURVE_EXPORT_COLUMNS,
        )
        writer.writeheader()

        for index, trade in enumerate(trades, start=1):
            row = trade_to_equity_curve_row(
                trade=trade,
                trade_number=index,
                starting_balance=running_balance,
                current_peak=running_peak,
                transaction_cost_calculator=transaction_cost_calculator,
            )
            writer.writerow(row)
            running_balance = row["ending_balance"]
            running_peak = row["running_peak"]

    return csv_path


def build_report(
    result: Any,
    csv_path: str | Path,
    symbol: str,
    timeframe: str,
    transaction_cost_calculator: TransactionCostCalculator | None = None,
) -> str:
    """
    Build a human-readable backtest report.
    """
    summary = result.performance_summary
    trades = tuple(result.trades)
    charges = total_transaction_charges(
        trades=trades,
        transaction_cost_calculator=transaction_cost_calculator,
    )
    net_pnl = net_total_pnl(
        gross_total_pnl=summary.total_pnl,
        trades=trades,
        transaction_cost_calculator=transaction_cost_calculator,
    )

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
        format_metric("Total Charges", charges),
        format_metric("Net PnL", net_pnl),
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
            format_metric("Closed Trades", len(trades)),
        ]
    )
    lines.extend(
        build_trade_details_section(
            trades=trades,
            transaction_cost_calculator=transaction_cost_calculator,
        )
    )
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
    transaction_cost_profile = build_transaction_cost_profile(
        brokerage_per_order=args.brokerage_per_order,
        stt_rate=args.stt_rate,
        exchange_transaction_charge_rate=args.exchange_transaction_charge_rate,
        sebi_charge_rate=args.sebi_charge_rate,
        stamp_duty_rate=args.stamp_duty_rate,
        gst_rate=args.gst_rate,
        cost_profile=args.cost_profile,
    )
    transaction_cost_calculator = build_transaction_cost_calculator(
        transaction_cost_profile
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
            transaction_cost_calculator=transaction_cost_calculator,
        )
    )

    if args.trades_output is not None:
        exported_path = export_trades_to_csv(
            trades=tuple(result.trades),
            output_path=args.trades_output,
            transaction_cost_calculator=transaction_cost_calculator,
        )

        print(format_metric("Trades Exported", exported_path))

    if args.equity_output is not None:
        exported_path = export_equity_curve_to_csv(
            trades=tuple(result.trades),
            output_path=args.equity_output,
            starting_balance=args.account_balance,
            transaction_cost_calculator=transaction_cost_calculator,
        )

        print(format_metric("Equity Curve Exported", exported_path))


if __name__ == "__main__":
    main()
