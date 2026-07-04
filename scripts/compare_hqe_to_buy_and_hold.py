"""
HQE vs Buy-and-Hold Benchmark

Compares HQE strategy equity curve against a simple buy-and-hold benchmark.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MARKET_CSV = Path("data/processed/fyers_nifty_5m_normalized.csv")
DEFAULT_EQUITY_CURVE_CSV = Path("data/processed/fyers_nifty_5m_equity_curve.csv")
DEFAULT_REPORT_OUTPUT = Path("data/processed/fyers_nifty_5m_benchmark_report.txt")
DEFAULT_SUMMARY_OUTPUT = Path("data/processed/fyers_nifty_5m_benchmark_summary.csv")
DEFAULT_INITIAL_BALANCE = 10000.0


@dataclass(frozen=True)
class BuyAndHoldResult:
    """
    Buy-and-hold benchmark result.
    """

    starting_balance: float
    first_close: float
    last_close: float
    units: float
    ending_balance: float
    net_pnl: float
    return_percent: float


@dataclass(frozen=True)
class StrategyResult:
    """
    HQE strategy result loaded from equity curve.
    """

    starting_balance: float
    ending_balance: float
    net_pnl: float
    return_percent: float
    total_trades: int


@dataclass(frozen=True)
class BenchmarkComparison:
    """
    Strategy vs benchmark comparison.
    """

    strategy: StrategyResult
    benchmark: BuyAndHoldResult
    alpha_amount: float
    alpha_percent: float
    outperformed: bool


def calculate_return_percent(starting_balance: float, ending_balance: float) -> float:
    """
    Calculate percentage return.
    """

    if starting_balance <= 0:
        raise ValueError("Starting balance must be positive.")

    return ((ending_balance - starting_balance) / starting_balance) * 100.0


def load_close_prices(market_csv_path: Path) -> list[float]:
    """
    Load close prices from a market CSV.
    """

    if not market_csv_path.exists():
        raise FileNotFoundError(f"Market CSV not found: {market_csv_path}")

    close_prices: list[float] = []

    with market_csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames or "close" not in reader.fieldnames:
            raise ValueError("Market CSV must contain a close column.")

        for row in reader:
            close_prices.append(float(row["close"]))

    return close_prices


def calculate_buy_and_hold(
    close_prices: list[float],
    starting_balance: float,
) -> BuyAndHoldResult:
    """
    Calculate buy-and-hold benchmark from first close to last close.
    """

    if len(close_prices) < 2:
        raise ValueError("At least two close prices are required.")

    first_close = close_prices[0]
    last_close = close_prices[-1]

    if first_close <= 0:
        raise ValueError("First close price must be positive.")

    units = starting_balance / first_close
    ending_balance = units * last_close
    net_pnl = ending_balance - starting_balance

    return BuyAndHoldResult(
        starting_balance=starting_balance,
        first_close=first_close,
        last_close=last_close,
        units=units,
        ending_balance=ending_balance,
        net_pnl=net_pnl,
        return_percent=calculate_return_percent(starting_balance, ending_balance),
    )


def load_strategy_result(
    equity_curve_csv_path: Path,
    starting_balance: float,
) -> StrategyResult:
    """
    Load HQE strategy result from equity curve CSV.
    """

    if not equity_curve_csv_path.exists():
        raise FileNotFoundError(f"Equity curve CSV not found: {equity_curve_csv_path}")

    with equity_curve_csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    if not rows:
        return StrategyResult(
            starting_balance=starting_balance,
            ending_balance=starting_balance,
            net_pnl=0.0,
            return_percent=0.0,
            total_trades=0,
        )

    last_row = rows[-1]

    if "ending_balance" not in last_row:
        raise ValueError("Equity curve CSV must contain ending_balance column.")

    ending_balance = float(last_row["ending_balance"])
    net_pnl = ending_balance - starting_balance

    return StrategyResult(
        starting_balance=starting_balance,
        ending_balance=ending_balance,
        net_pnl=net_pnl,
        return_percent=calculate_return_percent(starting_balance, ending_balance),
        total_trades=len(rows),
    )


def compare_strategy_to_benchmark(
    strategy: StrategyResult,
    benchmark: BuyAndHoldResult,
) -> BenchmarkComparison:
    """
    Compare HQE strategy to buy-and-hold benchmark.
    """

    alpha_amount = strategy.ending_balance - benchmark.ending_balance
    alpha_percent = strategy.return_percent - benchmark.return_percent

    return BenchmarkComparison(
        strategy=strategy,
        benchmark=benchmark,
        alpha_amount=alpha_amount,
        alpha_percent=alpha_percent,
        outperformed=alpha_amount > 0,
    )


def build_report(comparison: BenchmarkComparison) -> str:
    """
    Build human-readable benchmark report.
    """

    status = "OUTPERFORMED" if comparison.outperformed else "UNDERPERFORMED"

    return "\n".join(
        [
            "=" * 60,
            "Hunter Quant Engine - Benchmark Comparison",
            "=" * 60,
            "Benchmark: Buy and Hold",
            "-" * 60,
            "HQE STRATEGY",
            "-" * 60,
            f"Starting Balance: {comparison.strategy.starting_balance:.2f}",
            f"Ending Balance: {comparison.strategy.ending_balance:.2f}",
            f"Net PnL: {comparison.strategy.net_pnl:.2f}",
            f"Return %: {comparison.strategy.return_percent:.4f}",
            f"Total Trades: {comparison.strategy.total_trades}",
            "-" * 60,
            "BUY AND HOLD",
            "-" * 60,
            f"First Close: {comparison.benchmark.first_close:.2f}",
            f"Last Close: {comparison.benchmark.last_close:.2f}",
            f"Units Bought: {comparison.benchmark.units:.8f}",
            f"Ending Balance: {comparison.benchmark.ending_balance:.2f}",
            f"Net PnL: {comparison.benchmark.net_pnl:.2f}",
            f"Return %: {comparison.benchmark.return_percent:.4f}",
            "-" * 60,
            "COMPARISON",
            "-" * 60,
            f"Alpha Amount: {comparison.alpha_amount:.2f}",
            f"Alpha %: {comparison.alpha_percent:.4f}",
            f"Result: HQE {status} buy-and-hold",
            "=" * 60,
        ]
    )


def write_report(report: str, output_path: Path) -> None:
    """
    Write benchmark report.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")


def write_summary_csv(comparison: BenchmarkComparison, output_path: Path) -> None:
    """
    Write benchmark summary CSV.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "strategy_ending_balance",
                "strategy_net_pnl",
                "strategy_return_percent",
                "strategy_total_trades",
                "benchmark_ending_balance",
                "benchmark_net_pnl",
                "benchmark_return_percent",
                "alpha_amount",
                "alpha_percent",
                "outperformed",
            ]
        )

        writer.writerow(
            [
                comparison.strategy.ending_balance,
                comparison.strategy.net_pnl,
                comparison.strategy.return_percent,
                comparison.strategy.total_trades,
                comparison.benchmark.ending_balance,
                comparison.benchmark.net_pnl,
                comparison.benchmark.return_percent,
                comparison.alpha_amount,
                comparison.alpha_percent,
                comparison.outperformed,
            ]
        )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Compare HQE strategy against buy-and-hold benchmark."
    )

    parser.add_argument(
        "--market-csv",
        default=str(DEFAULT_MARKET_CSV),
        help="Market CSV with close column.",
    )
    parser.add_argument(
        "--equity-curve-csv",
        default=str(DEFAULT_EQUITY_CURVE_CSV),
        help="HQE equity curve CSV.",
    )
    parser.add_argument(
        "--initial-balance",
        type=float,
        default=DEFAULT_INITIAL_BALANCE,
        help="Initial balance used for comparison.",
    )
    parser.add_argument(
        "--report-output",
        default=str(DEFAULT_REPORT_OUTPUT),
        help="Output text report path.",
    )
    parser.add_argument(
        "--summary-output",
        default=str(DEFAULT_SUMMARY_OUTPUT),
        help="Output benchmark summary CSV path.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Run benchmark comparison.
    """

    args = parse_args()

    close_prices = load_close_prices(Path(args.market_csv))
    benchmark = calculate_buy_and_hold(close_prices, args.initial_balance)
    strategy = load_strategy_result(Path(args.equity_curve_csv), args.initial_balance)

    comparison = compare_strategy_to_benchmark(strategy, benchmark)
    report = build_report(comparison)

    write_report(report, Path(args.report_output))
    write_summary_csv(comparison, Path(args.summary_output))

    print(report)
    print(f"Report saved: {Path(args.report_output).resolve()}")
    print(f"Summary saved: {Path(args.summary_output).resolve()}")


if __name__ == "__main__":
    main()
