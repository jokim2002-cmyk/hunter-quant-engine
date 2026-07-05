"""
Benchmark Strategy Modes

Runs HQE SMC research for strict, balanced, and relaxed strategy modes,
then compares each mode against buy-and-hold after transaction costs.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.compare_hqe_to_buy_and_hold import (
    calculate_buy_and_hold,
    compare_strategy_to_benchmark,
    load_close_prices,
    load_strategy_result,
)
from scripts.run_fyers_nifty_research import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_PREFIX,
    DEFAULT_SYMBOL,
    DEFAULT_TIMEFRAME,
    build_output_paths,
    run_fyers_nifty_research,
)
from scripts.run_smc_research_workflow import (
    DEFAULT_ACCOUNT_BALANCE,
    DEFAULT_REWARD_TO_RISK,
    DEFAULT_RISK_PER_TRADE,
)
from src.config.strategy_config import supported_strategy_mode_names


DEFAULT_REPORT_OUTPUT = Path("data/processed/fyers_nifty_5m_mode_benchmark_report.txt")
DEFAULT_SUMMARY_OUTPUT = Path("data/processed/fyers_nifty_5m_mode_benchmark_summary.csv")


@dataclass(frozen=True)
class TradeCostSummary:
    """
    Aggregate trade cost summary loaded from exported trade CSV.
    """

    gross_pnl: float
    total_charges: float
    net_pnl: float
    total_trades: int


@dataclass(frozen=True)
class ModeBenchmarkResult:
    """
    Benchmark result for one strategy mode.
    """

    strategy_mode: str
    normalized_output_path: Path
    trades_output_path: Path
    equity_output_path: Path
    gross_pnl: float
    total_charges: float
    net_pnl: float
    strategy_return_percent: float
    benchmark_return_percent: float
    alpha_amount: float
    alpha_percent: float
    outperformed: bool
    total_trades: int
    runtime_seconds: float = 0.0


def load_trade_cost_summary(
    trades_csv_path: Path,
) -> TradeCostSummary:
    """
    Load gross PnL, charges, and net PnL from exported trade CSV.
    """
    if not trades_csv_path.exists():
        raise FileNotFoundError(f"Trades CSV not found: {trades_csv_path}")

    with trades_csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    if not rows:
        return TradeCostSummary(
            gross_pnl=0.0,
            total_charges=0.0,
            net_pnl=0.0,
            total_trades=0,
        )

    required_columns = {
        "pnl",
        "total_charges",
        "net_pnl",
    }

    missing_columns = required_columns.difference(rows[0].keys())

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Trades CSV missing required columns: {missing}")

    return TradeCostSummary(
        gross_pnl=sum(float(row["pnl"]) for row in rows),
        total_charges=sum(float(row["total_charges"]) for row in rows),
        net_pnl=sum(float(row["net_pnl"]) for row in rows),
        total_trades=len(rows),
    )


def benchmark_strategy_modes(
    input_path: str | Path,
    output_dir: str | Path,
    output_prefix: str,
    symbol: str,
    timeframe: str,
    account_balance: float,
    risk_per_trade: float,
    reward_to_risk: float,
    modes: tuple[str, ...] = supported_strategy_mode_names(),
    datetime_column: str | None = None,
    date_column: str | None = None,
    time_column: str | None = None,
    open_column: str | None = None,
    high_column: str | None = None,
    low_column: str | None = None,
    close_column: str | None = None,
    volume_column: str | None = None,
    default_volume: float = 0.0,
    max_candles: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    progress_callback: Callable[[str], None] | None = None,
    clock: Callable[[], float] = perf_counter,
) -> tuple[ModeBenchmarkResult, ...]:
    """
    Run each strategy mode and compare it against buy-and-hold.
    """
    results: list[ModeBenchmarkResult] = []

    for mode in modes:
        if progress_callback is not None:
            progress_callback(f"Running mode: {mode}")

        mode_started_at = clock()
        mode_output_prefix = f"{output_prefix}_{mode}"
        output_paths = build_output_paths(
            output_dir=output_dir,
            output_prefix=mode_output_prefix,
        )

        run_fyers_nifty_research(
            input_path=input_path,
            output_dir=output_dir,
            output_prefix=mode_output_prefix,
            symbol=symbol,
            timeframe=timeframe,
            account_balance=account_balance,
            risk_per_trade=risk_per_trade,
            reward_to_risk=reward_to_risk,
            strategy_mode=mode,
            datetime_column=datetime_column,
            date_column=date_column,
            time_column=time_column,
            open_column=open_column,
            high_column=high_column,
            low_column=low_column,
            close_column=close_column,
            volume_column=volume_column,
            default_volume=default_volume,
            max_candles=max_candles,
            start_date=start_date,
            end_date=end_date,
        )

        close_prices = load_close_prices(output_paths.normalized_output_path)
        benchmark = calculate_buy_and_hold(
            close_prices=close_prices,
            starting_balance=account_balance,
        )
        strategy = load_strategy_result(
            equity_curve_csv_path=output_paths.equity_output_path,
            starting_balance=account_balance,
        )
        comparison = compare_strategy_to_benchmark(
            strategy=strategy,
            benchmark=benchmark,
        )
        trade_cost_summary = load_trade_cost_summary(output_paths.trades_output_path)
        runtime_seconds = clock() - mode_started_at

        if progress_callback is not None:
            progress_callback(
                f"Finished mode: {mode} in {runtime_seconds:.2f} seconds"
            )

        results.append(
            ModeBenchmarkResult(
                strategy_mode=mode,
                normalized_output_path=output_paths.normalized_output_path,
                trades_output_path=output_paths.trades_output_path,
                equity_output_path=output_paths.equity_output_path,
                gross_pnl=trade_cost_summary.gross_pnl,
                total_charges=trade_cost_summary.total_charges,
                net_pnl=trade_cost_summary.net_pnl,
                strategy_return_percent=strategy.return_percent,
                benchmark_return_percent=benchmark.return_percent,
                alpha_amount=comparison.alpha_amount,
                alpha_percent=comparison.alpha_percent,
                outperformed=comparison.outperformed,
                total_trades=trade_cost_summary.total_trades,
                runtime_seconds=runtime_seconds,
            )
        )

    return tuple(results)


def result_status(
    result: ModeBenchmarkResult,
) -> str:
    """
    Return human-readable benchmark status.
    """
    if result.outperformed:
        return "OUTPERFORMED"

    return "UNDERPERFORMED"


def total_runtime_seconds(
    results: tuple[ModeBenchmarkResult, ...],
) -> float:
    """
    Return total runtime across all benchmarked modes.
    """
    return sum(result.runtime_seconds for result in results)


def build_report(
    results: tuple[ModeBenchmarkResult, ...],
) -> str:
    """
    Build human-readable mode benchmark report.
    """
    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - Strategy Mode Benchmark",
        "============================================================",
        "Benchmark: Buy and Hold",
        "Costs: Included through exported net equity curve and trade charges",
        "------------------------------------------------------------",
        (
            "Mode | Trades | Gross PnL | Charges | Net PnL | "
            "HQE Return % | BuyHold Return % | Alpha % | Result | Runtime Seconds"
        ),
        "------------------------------------------------------------",
    ]

    for result in results:
        lines.append(
            (
                f"{result.strategy_mode} | "
                f"{result.total_trades} | "
                f"{result.gross_pnl:.2f} | "
                f"{result.total_charges:.2f} | "
                f"{result.net_pnl:.2f} | "
                f"{result.strategy_return_percent:.4f} | "
                f"{result.benchmark_return_percent:.4f} | "
                f"{result.alpha_percent:.4f} | "
                f"HQE {result_status(result)} buy-and-hold | "
                f"{result.runtime_seconds:.2f}"
            )
        )

    lines.extend(
        [
            "------------------------------------------------------------",
            f"Total Runtime Seconds: {total_runtime_seconds(results):.2f}",
            "============================================================",
            "",
        ]
    )

    return "\n".join(lines)


def write_report(
    report: str,
    output_path: Path,
) -> None:
    """
    Write mode benchmark report.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")


def write_summary_csv(
    results: tuple[ModeBenchmarkResult, ...],
    output_path: Path,
) -> None:
    """
    Write mode benchmark summary CSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            [
                "strategy_mode",
                "total_trades",
                "gross_pnl",
                "total_charges",
                "net_pnl",
                "strategy_return_percent",
                "benchmark_return_percent",
                "alpha_amount",
                "alpha_percent",
                "outperformed",
                "normalized_output_path",
                "trades_output_path",
                "equity_output_path",
                "runtime_seconds",
            ]
        )

        for result in results:
            writer.writerow(
                [
                    result.strategy_mode,
                    result.total_trades,
                    result.gross_pnl,
                    result.total_charges,
                    result.net_pnl,
                    result.strategy_return_percent,
                    result.benchmark_return_percent,
                    result.alpha_amount,
                    result.alpha_percent,
                    result.outperformed,
                    result.normalized_output_path,
                    result.trades_output_path,
                    result.equity_output_path,
                    result.runtime_seconds,
                ]
            )


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Benchmark strict, balanced, and relaxed HQE strategy modes.",
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Raw FYERS NIFTY CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for benchmark outputs.",
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PREFIX,
        help="Base output prefix. Mode name is appended automatically.",
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
        help="Risk per trade as decimal.",
    )
    parser.add_argument(
        "--reward-to-risk",
        type=float,
        default=DEFAULT_REWARD_TO_RISK,
        help="Reward-to-risk multiple used for take-profit planning.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(supported_strategy_mode_names()),
        choices=supported_strategy_mode_names(),
        help="Strategy modes to benchmark.",
    )
    parser.add_argument(
        "--datetime-column",
        default=None,
        help="Input datetime/timestamp column name.",
    )
    parser.add_argument(
        "--date-column",
        default=None,
        help="Input date column name when date and time are separate.",
    )
    parser.add_argument(
        "--time-column",
        default=None,
        help="Input time column name when date and time are separate.",
    )
    parser.add_argument(
        "--open-column",
        default=None,
        help="Input open column name.",
    )
    parser.add_argument(
        "--high-column",
        default=None,
        help="Input high column name.",
    )
    parser.add_argument(
        "--low-column",
        default=None,
        help="Input low column name.",
    )
    parser.add_argument(
        "--close-column",
        default=None,
        help="Input close column name.",
    )
    parser.add_argument(
        "--volume-column",
        default=None,
        help="Input volume column name.",
    )
    parser.add_argument(
        "--default-volume",
        type=float,
        default=0.0,
        help="Volume value used when no volume column exists.",
    )
    parser.add_argument(
        "--max-candles",
        type=int,
        default=None,
        help=(
            "Limit each mode benchmark to the latest N normalized candles. "
            "Useful for safe partial runs."
        ),
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Inclusive normalized candle start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Inclusive normalized candle end date in YYYY-MM-DD format.",
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

    return parser


def main() -> None:
    """
    Run strategy mode benchmark.
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    results = benchmark_strategy_modes(
        input_path=args.input,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        symbol=args.symbol,
        timeframe=args.timeframe,
        account_balance=args.account_balance,
        risk_per_trade=args.risk_per_trade,
        reward_to_risk=args.reward_to_risk,
        modes=tuple(args.modes),
        datetime_column=args.datetime_column,
        date_column=args.date_column,
        time_column=args.time_column,
        open_column=args.open_column,
        high_column=args.high_column,
        low_column=args.low_column,
        close_column=args.close_column,
        volume_column=args.volume_column,
        default_volume=args.default_volume,
        max_candles=args.max_candles,
        start_date=args.start_date,
        end_date=args.end_date,
        progress_callback=print,
    )

    report = build_report(results)

    write_report(report, Path(args.report_output))
    write_summary_csv(results, Path(args.summary_output))

    print(report)
    print(f"Report saved: {Path(args.report_output).resolve()}")
    print(f"Summary saved: {Path(args.summary_output).resolve()}")


if __name__ == "__main__":
    main()
