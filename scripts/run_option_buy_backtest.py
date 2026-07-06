"""
Run Offline Option Buy Backtest

Runs an offline option-buy backtest from supplied broker-agnostic CSV files.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backtesting.option_buy_backtest_runner import OptionBuyBacktestRunner
from src.backtesting.option_buy_backtest_scenario_csv_loader import (
    OptionBuyBacktestScenarioCsvLoader,
)
from src.backtesting.option_buy_backtest_summary import OptionBuyBacktestSummary
from src.backtesting.option_premium_candle_csv_loader import (
    OptionPremiumCandleCsvLoader,
)


def run_backtest(
    scenario_csv: str | Path,
    premium_csv: str | Path,
) -> OptionBuyBacktestSummary:
    """
    Run an offline option-buy backtest from scenario and premium CSV files.
    """
    scenarios = OptionBuyBacktestScenarioCsvLoader().load_scenarios(scenario_csv)
    premium_provider = OptionPremiumCandleCsvLoader().load_provider(premium_csv)

    signals = tuple(scenario.signal for scenario in scenarios)
    snapshots = tuple(scenario.snapshot for scenario in scenarios)

    return OptionBuyBacktestRunner().run(
        signals=signals,
        snapshots=snapshots,
        premium_candle_provider=premium_provider,
    )


def format_summary(
    summary: OptionBuyBacktestSummary,
) -> str:
    """
    Format an option-buy backtest summary as stable text.
    """
    lines = [
        "Hunter Quant Engine - Offline Option Buy Backtest",
        f"Planned signals: {summary.planned_signals}",
        f"Completed trades: {summary.completed_trades}",
        f"Rejected plans: {summary.rejected_plans}",
        f"Failed backtests: {summary.failed_backtests}",
        f"Winning trades: {summary.winning_trades}",
        f"Losing trades: {summary.losing_trades}",
        f"Breakeven trades: {summary.breakeven_trades}",
        f"Win rate: {summary.win_rate * 100:.2f}%",
        f"Total gross P&L: {summary.total_gross_pnl:.2f}",
        f"Total estimated charges: {summary.total_estimated_charges:.2f}",
        f"Total net P&L: {summary.total_net_pnl:.2f}",
    ]

    if summary.rejection_reasons:
        lines.append("Rejection reasons:")
        lines.extend(f"- {reason}" for reason in summary.rejection_reasons)

    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Run an offline HQE option-buy backtest from CSV files.",
    )
    parser.add_argument(
        "--scenario-csv",
        required=True,
        help="Path to option-buy backtest scenario CSV.",
    )
    parser.add_argument(
        "--premium-csv",
        required=True,
        help="Path to option premium candle CSV.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """
    CLI entrypoint.
    """
    args = build_argument_parser().parse_args(argv)
    summary = run_backtest(
        scenario_csv=args.scenario_csv,
        premium_csv=args.premium_csv,
    )
    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())