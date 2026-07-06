"""
Run Offline Option Buy Backtest

Runs an offline option-buy backtest from supplied broker-agnostic CSV files.
"""

import argparse
import csv
import json
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


def summary_to_dict(summary: OptionBuyBacktestSummary) -> dict[str, object]:
    """
    Convert a backtest summary into a serializable dictionary.
    """
    return {
        "planned_signals": summary.planned_signals,
        "completed_trades": summary.completed_trades,
        "rejected_plans": summary.rejected_plans,
        "failed_backtests": summary.failed_backtests,
        "winning_trades": summary.winning_trades,
        "losing_trades": summary.losing_trades,
        "breakeven_trades": summary.breakeven_trades,
        "win_rate": summary.win_rate,
        "total_gross_pnl": summary.total_gross_pnl,
        "total_estimated_charges": summary.total_estimated_charges,
        "total_net_pnl": summary.total_net_pnl,
        "rejection_reasons": list(summary.rejection_reasons),
    }


def write_summary_json(
    summary: OptionBuyBacktestSummary,
    output_path: str | Path,
) -> None:
    """
    Write a backtest summary to a JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(summary_to_dict(summary), handle, indent=2)
        handle.write("\n")


def write_summary_csv(
    summary: OptionBuyBacktestSummary,
    output_path: str | Path,
) -> None:
    """
    Write a backtest summary to a CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = summary_to_dict(summary)
    header = [
        "planned_signals",
        "completed_trades",
        "rejected_plans",
        "failed_backtests",
        "winning_trades",
        "losing_trades",
        "breakeven_trades",
        "win_rate",
        "total_gross_pnl",
        "total_estimated_charges",
        "total_net_pnl",
        "rejection_reasons",
    ]
    row = [
        payload["planned_signals"],
        payload["completed_trades"],
        payload["rejected_plans"],
        payload["failed_backtests"],
        payload["winning_trades"],
        payload["losing_trades"],
        payload["breakeven_trades"],
        payload["win_rate"],
        payload["total_gross_pnl"],
        payload["total_estimated_charges"],
        payload["total_net_pnl"],
        ";".join(str(reason) for reason in payload["rejection_reasons"]),
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerow(row)


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
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Optional path to write the summary as JSON.",
    )
    parser.add_argument(
        "--summary-csv",
        default=None,
        help="Optional path to write the summary as CSV.",
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

    if args.summary_json:
        write_summary_json(summary, args.summary_json)

    if args.summary_csv:
        write_summary_csv(summary, args.summary_csv)

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())