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
from src.backtesting.option_buy_backtest_scenario_builder import (
    OptionBuyBacktestScenarioBuilder,
)
from src.backtesting.option_buy_backtest_scenario_csv_loader import (
    OptionBuyBacktestScenarioCsvLoader,
)
from src.backtesting.option_buy_backtest_summary import OptionBuyBacktestSummary
from src.backtesting.option_chain_snapshot_csv_loader import (
    OptionChainSnapshotCsvLoader,
)
from src.backtesting.option_premium_backtest_result import (
    OptionPremiumBacktestResult,
)
from src.backtesting.option_premium_candle_csv_loader import (
    OptionPremiumCandleCsvLoader,
)
from src.backtesting.trade_signal_csv_loader import TradeSignalCsvLoader
from src.backtesting.time_scoped_option_premium_candle_provider import (
    TimeScopedOptionPremiumCandleProvider,
)
from src.costs.transaction_cost_calculator import TransactionCostCalculator
from src.costs.transaction_cost_profile_preset import (
    COST_PROFILE_CUSTOM,
    build_transaction_cost_profile_from_name,
    supported_transaction_cost_profile_names,
)
from src.trade_planning.dynamic_option_strike_selector import (
    DynamicOptionStrikeSelector,
    OptionLiquidityFilterConfig,
)
from src.trade_planning.fixed_percent_option_premium_trade_level_planner import (
    FixedPercentOptionPremiumTradeLevelPlanner,
)
from src.trade_planning.option_buy_planner import OptionBuyPlanner
from src.trade_planning.option_buy_trade_plan_builder import OptionBuyTradePlanBuilder
from src.trade_planning.option_premium_trade_level_config import (
    OptionPremiumTradeLevelConfig,
)


def load_scenarios_from_inputs(
    scenario_csv: str | Path | None = None,
    signal_csv: str | Path | None = None,
    snapshot_csv: str | Path | None = None,
) -> tuple[object, ...]:
    """
    Load scenarios from either scenario CSV input or separate signal/snapshot CSV inputs.
    """
    if scenario_csv is not None and (signal_csv is not None or snapshot_csv is not None):
        raise ValueError("scenario_csv cannot be combined with signal_csv or snapshot_csv")

    if scenario_csv is None and (signal_csv is None or snapshot_csv is None):
        raise ValueError("scenario_csv or both signal_csv and snapshot_csv are required")

    if scenario_csv is not None:
        scenarios = OptionBuyBacktestScenarioCsvLoader().load_scenarios(scenario_csv)
        return tuple(scenarios)

    signals = TradeSignalCsvLoader().load_signals(signal_csv)
    snapshots = OptionChainSnapshotCsvLoader().load_snapshots(snapshot_csv)
    return OptionBuyBacktestScenarioBuilder().build_scenarios(signals, snapshots)


def build_option_buy_backtest_runner(
    *,
    min_volume: int = 0,
    min_open_interest: int = 0,
    require_bid_ask_quote: bool = False,
    max_spread: float | None = None,
    stop_loss_percent: float = 0.30,
    target_percent: float = 0.60,
    entry_slippage_percent: float = 0.0,
    lots: int = 1,
    cost_profile: str = COST_PROFILE_CUSTOM,
    min_estimated_net_reward: float = 0.0,
) -> OptionBuyBacktestRunner:
    """
    Build an option-buy backtest runner with explicit robustness controls.
    """
    transaction_cost_profile = build_transaction_cost_profile_from_name(cost_profile)
    cost_calculator = TransactionCostCalculator(transaction_cost_profile)

    planner = OptionBuyPlanner(
        strike_selector=DynamicOptionStrikeSelector(
            liquidity_config=OptionLiquidityFilterConfig(
                min_volume=min_volume,
                min_open_interest=min_open_interest,
                require_bid_ask_quote=require_bid_ask_quote,
                max_spread=max_spread,
            )
        ),
        premium_level_planner=FixedPercentOptionPremiumTradeLevelPlanner(
            config=OptionPremiumTradeLevelConfig(
                stop_loss_percent=stop_loss_percent,
                target_percent=target_percent,
                entry_slippage_percent=entry_slippage_percent,
            )
        ),
        trade_plan_builder=OptionBuyTradePlanBuilder(
            lots=lots,
            cost_calculator=cost_calculator,
            min_estimated_net_reward=min_estimated_net_reward,
        ),
    )
    return OptionBuyBacktestRunner(planner=planner)


def build_option_buy_backtest_runner(
    *,
    min_volume: int = 0,
    min_open_interest: int = 0,
    require_bid_ask_quote: bool = False,
    max_spread: float | None = None,
    stop_loss_percent: float = 0.30,
    target_percent: float = 0.60,
    entry_slippage_percent: float = 0.0,
    lots: int = 1,
    cost_profile: str = COST_PROFILE_CUSTOM,
    min_estimated_net_reward: float = 0.0,
) -> OptionBuyBacktestRunner:
    """
    Build an option-buy backtest runner with explicit robustness controls.
    """
    transaction_cost_profile = build_transaction_cost_profile_from_name(cost_profile)
    cost_calculator = TransactionCostCalculator(transaction_cost_profile)

    planner = OptionBuyPlanner(
        strike_selector=DynamicOptionStrikeSelector(
            liquidity_config=OptionLiquidityFilterConfig(
                min_volume=min_volume,
                min_open_interest=min_open_interest,
                require_bid_ask_quote=require_bid_ask_quote,
                max_spread=max_spread,
            )
        ),
        premium_level_planner=FixedPercentOptionPremiumTradeLevelPlanner(
            config=OptionPremiumTradeLevelConfig(
                stop_loss_percent=stop_loss_percent,
                target_percent=target_percent,
                entry_slippage_percent=entry_slippage_percent,
            )
        ),
        trade_plan_builder=OptionBuyTradePlanBuilder(
            lots=lots,
            cost_calculator=cost_calculator,
            min_estimated_net_reward=min_estimated_net_reward,
        ),
    )
    return OptionBuyBacktestRunner(planner=planner)


def run_backtest(
    scenario_csv: str | Path | None = None,
    premium_csv: str | Path | None = None,
    signal_csv: str | Path | None = None,
    snapshot_csv: str | Path | None = None,
    min_volume: int = 0,
    min_open_interest: int = 0,
    require_bid_ask_quote: bool = False,
    max_spread: float | None = None,
    stop_loss_percent: float = 0.30,
    target_percent: float = 0.60,
    entry_slippage_percent: float = 0.0,
    lots: int = 1,
    cost_profile: str = COST_PROFILE_CUSTOM,
    min_estimated_net_reward: float = 0.0,
    time_scope_premium_candles: bool = False,
    max_bars_held: int | None = None,
) -> OptionBuyBacktestSummary:
    """
    Run an offline option-buy backtest from scenario and premium CSV files.
    """
    scenarios = load_scenarios_from_inputs(
        scenario_csv=scenario_csv,
        signal_csv=signal_csv,
        snapshot_csv=snapshot_csv,
    )
    premium_provider = OptionPremiumCandleCsvLoader().load_provider(premium_csv)
    if time_scope_premium_candles or max_bars_held is not None:
        premium_provider = TimeScopedOptionPremiumCandleProvider(
            delegate=premium_provider,
            max_bars_held=max_bars_held,
        )

    signals = tuple(scenario.signal for scenario in scenarios)
    snapshots = tuple(scenario.snapshot for scenario in scenarios)

    return build_option_buy_backtest_runner(
        min_volume=min_volume,
        min_open_interest=min_open_interest,
        require_bid_ask_quote=require_bid_ask_quote,
        max_spread=max_spread,
        stop_loss_percent=stop_loss_percent,
        target_percent=target_percent,
        entry_slippage_percent=entry_slippage_percent,
        lots=lots,
        cost_profile=cost_profile,
        min_estimated_net_reward=min_estimated_net_reward,
    ).run(
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


def trade_result_to_dict(result: OptionPremiumBacktestResult) -> dict[str, object]:
    """
    Convert a single backtest trade result into a serializable dictionary.
    """
    return {
        "symbol": result.plan.entry.contract.symbol,
        "option_type": result.plan.entry.contract.option_type.value,
        "strike_price": result.plan.entry.contract.strike_price,
        "expiry_date": result.plan.entry.contract.expiry_date.isoformat(),
        "entry_premium": result.plan.entry_premium,
        "stop_loss_premium": result.plan.stop_loss_premium,
        "target_premium": result.plan.target_premium,
        "exit_premium": result.exit_premium,
        "exit_reason": result.exit_reason.value,
        "quantity": result.quantity,
        "bars_held": result.bars_held,
        "estimated_charges": result.estimated_charges,
        "gross_pnl": result.gross_pnl,
        "net_pnl": result.net_pnl,
        "return_percent": result.return_percent,
        "is_win": result.is_win,
        "is_loss": result.is_loss,
    }


def trade_results_to_dicts(
    results: Sequence[OptionPremiumBacktestResult],
) -> list[dict[str, object]]:
    """
    Convert a sequence of backtest trade results into serializable dictionaries.
    """
    return [trade_result_to_dict(result) for result in results]


def write_trades_json(
    results: Sequence[OptionPremiumBacktestResult],
    output_path: str | Path,
) -> None:
    """
    Write per-trade results to a JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(trade_results_to_dicts(results), handle, indent=2)
        handle.write("\n")


def write_trades_csv(
    results: Sequence[OptionPremiumBacktestResult],
    output_path: str | Path,
) -> None:
    """
    Write per-trade results to a CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = trade_results_to_dicts(results)
    header = [
        "symbol",
        "option_type",
        "strike_price",
        "expiry_date",
        "entry_premium",
        "stop_loss_premium",
        "target_premium",
        "exit_premium",
        "exit_reason",
        "quantity",
        "bars_held",
        "estimated_charges",
        "gross_pnl",
        "net_pnl",
        "return_percent",
        "is_win",
        "is_loss",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([row[field] for field in header])


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
        default=None,
        help="Path to option-buy backtest scenario CSV.",
    )
    parser.add_argument(
        "--signal-csv",
        default=None,
        help="Path to trade signal CSV.",
    )
    parser.add_argument(
        "--snapshot-csv",
        default=None,
        help="Path to option chain snapshot CSV.",
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
    parser.add_argument(
        "--trades-json",
        default=None,
        help="Optional path to write per-trade results as JSON.",
    )
    parser.add_argument(
        "--trades-csv",
        default=None,
        help="Optional path to write per-trade results as CSV.",
    )

    parser.add_argument(
        "--min-volume",
        type=int,
        default=0,
        help="Minimum option chain entry volume required for strike selection.",
    )
    parser.add_argument(
        "--min-open-interest",
        type=int,
        default=0,
        help="Minimum option chain entry open interest required for strike selection.",
    )
    parser.add_argument(
        "--require-bid-ask-quote",
        action="store_true",
        help="Reject option entries without both bid and ask quote.",
    )
    parser.add_argument(
        "--max-spread",
        type=float,
        default=None,
        help="Maximum absolute bid/ask spread allowed for strike selection.",
    )
    parser.add_argument(
        "--stop-loss-percent",
        type=float,
        default=0.30,
        help="Option premium stop-loss percent. Default: 0.30.",
    )
    parser.add_argument(
        "--target-percent",
        type=float,
        default=0.60,
        help="Option premium target percent. Default: 0.60.",
    )
    parser.add_argument(
        "--entry-slippage-percent",
        type=float,
        default=0.0,
        help="Buyer-adverse entry slippage percent applied before planning levels.",
    )
    parser.add_argument(
        "--lots",
        type=int,
        default=1,
        help="Number of option lots per plan.",
    )
    parser.add_argument(
        "--cost-profile",
        default=COST_PROFILE_CUSTOM,
        choices=supported_transaction_cost_profile_names(),
        help="Transaction cost profile used for planned target-exit charge estimate.",
    )
    parser.add_argument(
        "--min-estimated-net-reward",
        type=float,
        default=0.0,
        help="Reject plans whose estimated net target reward is below this value.",
    )

    parser.add_argument(
        "--time-scope-premium-candles",
        action="store_true",
        help="Replay only option premium candles at or after the signal timestamp.",
    )
    parser.add_argument(
        "--max-bars-held",
        type=int,
        default=None,
        help="Maximum number of post-signal premium bars to replay per option plan.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """
    CLI entrypoint.
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.scenario_csv is None and args.signal_csv is None and args.snapshot_csv is None:
        parser.error("either --scenario-csv or both --signal-csv and --snapshot-csv are required")

    if args.scenario_csv is not None and (args.signal_csv is not None or args.snapshot_csv is not None):
        parser.error("--scenario-csv cannot be used with --signal-csv or --snapshot-csv")

    if (args.signal_csv is None) != (args.snapshot_csv is None):
        parser.error("--signal-csv and --snapshot-csv must be provided together")

    summary = run_backtest(
        scenario_csv=args.scenario_csv,
        premium_csv=args.premium_csv,
        signal_csv=args.signal_csv,
        snapshot_csv=args.snapshot_csv,
        min_volume=args.min_volume,
        min_open_interest=args.min_open_interest,
        require_bid_ask_quote=args.require_bid_ask_quote,
        max_spread=args.max_spread,
        stop_loss_percent=args.stop_loss_percent,
        target_percent=args.target_percent,
        entry_slippage_percent=args.entry_slippage_percent,
        lots=args.lots,
        cost_profile=args.cost_profile,
        min_estimated_net_reward=args.min_estimated_net_reward,
        time_scope_premium_candles=args.time_scope_premium_candles,
        max_bars_held=args.max_bars_held,
    )

    if args.summary_json:
        write_summary_json(summary, args.summary_json)

    if args.summary_csv:
        write_summary_csv(summary, args.summary_csv)

    if args.trades_json:
        write_trades_json(summary.results, args.trades_json)

    if args.trades_csv:
        write_trades_csv(summary.results, args.trades_csv)

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())