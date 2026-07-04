"""
Diagnose SMC Backtest

Diagnostic script for explaining why an SMC backtest produced zero or few
trades. It reports detection counts, signal counts, candidate counts,
trade plan counts, de-duplication counts, and closed trade counts.
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtesting.backtest_engine import BacktestEngine
from src.config.strategy_config import (
    DEFAULT_SMC_STRATEGY_CONFIG,
    smc_strategy_config_for_mode,
    supported_strategy_mode_names,
)
from src.backtesting.trade_plan_deduplicator import TradePlanDeduplicator
from src.historical_data.providers.csv_historical_data_provider import (
    CSVHistoricalDataProvider,
)
from src.historical_data.providers.in_memory_historical_data_provider import (
    InMemoryHistoricalDataProvider,
)
from src.models.candle import Candle
from src.risk.risk_manager import RiskManager
from src.risk.risk_profile import RiskProfile
from src.risk.trade_plan import TradePlan
from src.strategy.context_factories.default_strategy_context_factory import (
    DefaultStrategyContextFactory,
)
from src.strategy.signal_type import SignalType
from src.strategy.smc_strategy import SMCStrategy
from src.strategy.strategy_context import StrategyContext
from src.trade_planning.smc_trade_candidate_planner import (
    SMCTradeCandidatePlanner,
)


DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "nifty_5min.csv"
DEFAULT_SYMBOL = "NIFTY"
DEFAULT_TIMEFRAME = "5m"
DEFAULT_ACCOUNT_BALANCE = 10000.0
DEFAULT_RISK_PER_TRADE = 0.01
DEFAULT_REWARD_TO_RISK = 2.0
DEFAULT_STRATEGY_MODE = DEFAULT_SMC_STRATEGY_CONFIG.mode.value
EMPTY_ANALYSIS_TIME = datetime(1970, 1, 1)


@dataclass(frozen=True)
class DiagnosticSummary:
    """
    Immutable diagnostic summary for an SMC backtest run.
    """

    csv_path: Path
    symbol: str
    timeframe: str

    candles_loaded: int

    market_structure_points: int
    bos_events: int
    choch_events: int
    liquidity_points: int
    equal_high_points: int
    equal_low_points: int
    liquidity_clusters: int
    liquidity_sweeps: int
    fair_value_gaps: int
    order_blocks: int

    long_signals: int
    short_signals: int
    neutral_signals: int

    trade_candidates: int
    trade_plans_before_deduplication: int
    duplicate_trade_plans_removed: int
    trade_plans_after_deduplication: int

    closed_trades: int
    total_pnl: float
    strategy_mode: str = DEFAULT_STRATEGY_MODE


@dataclass(frozen=True)
class WalkForwardDiagnostics:
    """
    Immutable walk-forward diagnostic counters.
    """

    long_signals: int
    short_signals: int
    neutral_signals: int
    trade_candidates: int
    trade_plans_created: tuple[TradePlan, ...]


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Build command-line argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Diagnose HQE SMC backtest signal generation.",
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
        "--strategy-mode",
        default=DEFAULT_STRATEGY_MODE,
        choices=supported_strategy_mode_names(),
        help="SMC strategy mode: strict, balanced, or relaxed.",
    )

    return parser


def build_risk_profile(
    account_balance: float,
    risk_per_trade: float,
    reward_to_risk: float,
) -> RiskProfile:
    """
    Build immutable risk profile for diagnostic run.

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


def load_candles(
    csv_path: str | Path,
) -> tuple[Candle, ...]:
    """
    Load candles from CSV.

    Args:
        csv_path: CSV historical data path.

    Returns:
        Tuple of immutable candles.
    """
    return CSVHistoricalDataProvider(csv_path).load()


def create_final_context(
    candles: tuple[Candle, ...],
    symbol: str,
    timeframe: str,
) -> StrategyContext:
    """
    Create final full-history StrategyContext for detection diagnostics.

    Args:
        candles: Historical candles.
        symbol: Market symbol.
        timeframe: Market timeframe.

    Returns:
        Immutable StrategyContext.
    """
    analysis_time = candles[-1].datetime if candles else EMPTY_ANALYSIS_TIME

    return DefaultStrategyContextFactory().create(
        symbol=symbol,
        timeframe=timeframe,
        analysis_time=analysis_time,
        candles=candles,
    )


def run_walk_forward_diagnostics(
    candles: tuple[Candle, ...],
    symbol: str,
    timeframe: str,
    risk_profile: RiskProfile,
    strategy_mode: str = DEFAULT_STRATEGY_MODE,
) -> WalkForwardDiagnostics:
    """
    Run strategy, trade candidate planning, and risk planning in walk-forward mode.

    Args:
        candles: Historical candles.
        symbol: Market symbol.
        timeframe: Market timeframe.
        risk_profile: Immutable risk profile.

    Returns:
        Immutable walk-forward diagnostic counters.
    """
    context_factory = DefaultStrategyContextFactory()
    strategy = SMCStrategy(
        config=smc_strategy_config_for_mode(strategy_mode),
    )
    trade_candidate_planner = SMCTradeCandidatePlanner()
    risk_manager = RiskManager()

    long_signals = 0
    short_signals = 0
    neutral_signals = 0
    trade_candidates = 0
    trade_plans: list[TradePlan] = []

    for index, candle in enumerate(candles):
        context = context_factory.create(
            symbol=symbol,
            timeframe=timeframe,
            analysis_time=candle.datetime,
            candles=candles[: index + 1],
        )

        signals = strategy.generate(context)

        for signal in signals:
            if signal.signal_type == SignalType.LONG:
                long_signals += 1

            if signal.signal_type == SignalType.SHORT:
                short_signals += 1

            if signal.signal_type == SignalType.NEUTRAL:
                neutral_signals += 1

            candidates = trade_candidate_planner.plan(
                signal=signal,
                context=context,
            )
            trade_candidates += len(candidates)

            for candidate in candidates:
                plans = risk_manager.plan(
                    signal=candidate.signal,
                    risk_profile=risk_profile,
                    entry_price=candidate.entry_price,
                    stop_loss=candidate.stop_loss,
                )
                trade_plans.extend(plans)

    return WalkForwardDiagnostics(
        long_signals=long_signals,
        short_signals=short_signals,
        neutral_signals=neutral_signals,
        trade_candidates=trade_candidates,
        trade_plans_created=tuple(trade_plans),
    )


def diagnose(
    csv_path: str | Path,
    symbol: str,
    timeframe: str,
    risk_profile: RiskProfile,
    strategy_mode: str = DEFAULT_STRATEGY_MODE,
) -> DiagnosticSummary:
    """
    Build full diagnostic summary.

    Args:
        csv_path: CSV historical data path.
        symbol: Market symbol.
        timeframe: Market timeframe.
        risk_profile: Immutable risk profile.

    Returns:
        Immutable DiagnosticSummary.
    """
    candles = load_candles(csv_path)
    final_context = create_final_context(
        candles=candles,
        symbol=symbol,
        timeframe=timeframe,
    )
    walk_forward = run_walk_forward_diagnostics(
        candles=candles,
        symbol=symbol,
        timeframe=timeframe,
        risk_profile=risk_profile,
        strategy_mode=strategy_mode,
    )

    trade_plans_before_deduplication = len(walk_forward.trade_plans_created)
    deduplicated_trade_plans = TradePlanDeduplicator().deduplicate(
        walk_forward.trade_plans_created
    )
    trade_plans_after_deduplication = len(deduplicated_trade_plans)
    duplicate_trade_plans_removed = (
        trade_plans_before_deduplication - trade_plans_after_deduplication
    )

    backtest_result = BacktestEngine(
        trade_plans=deduplicated_trade_plans,
        historical_data_provider=InMemoryHistoricalDataProvider(candles),
    ).run()

    return DiagnosticSummary(
        csv_path=Path(csv_path),
        symbol=symbol,
        timeframe=timeframe,
        candles_loaded=len(candles),
        market_structure_points=len(final_context.market_structure_points),
        bos_events=len(final_context.bos_events),
        choch_events=len(final_context.choch_events),
        liquidity_points=len(final_context.liquidity_points),
        equal_high_points=len(final_context.equal_high_points),
        equal_low_points=len(final_context.equal_low_points),
        liquidity_clusters=len(final_context.liquidity_clusters),
        liquidity_sweeps=len(final_context.liquidity_sweeps),
        fair_value_gaps=len(final_context.fair_value_gaps),
        order_blocks=len(final_context.order_blocks),
        long_signals=walk_forward.long_signals,
        short_signals=walk_forward.short_signals,
        neutral_signals=walk_forward.neutral_signals,
        trade_candidates=walk_forward.trade_candidates,
        trade_plans_before_deduplication=trade_plans_before_deduplication,
        duplicate_trade_plans_removed=duplicate_trade_plans_removed,
        trade_plans_after_deduplication=trade_plans_after_deduplication,
        closed_trades=len(backtest_result.trades),
        total_pnl=backtest_result.performance_summary.total_pnl,
        strategy_mode=strategy_mode,
    )


def format_metric(
    label: str,
    value,
) -> str:
    """
    Format a diagnostic metric line.

    Args:
        label: Metric label.
        value: Metric value.

    Returns:
        Formatted metric line.
    """
    return f"{label}: {value}"


def build_report(
    summary: DiagnosticSummary,
) -> str:
    """
    Build human-readable diagnostic report.

    Args:
        summary: Immutable diagnostic summary.

    Returns:
        Multiline diagnostic report.
    """
    lines = [
        "",
        "============================================================",
        "Hunter Quant Engine - SMC Diagnostic Report",
        "============================================================",
        format_metric("CSV", summary.csv_path),
        format_metric("Symbol", summary.symbol),
        format_metric("Timeframe", summary.timeframe),
        format_metric("Strategy Mode", summary.strategy_mode),
        "------------------------------------------------------------",
        "DATA",
        "------------------------------------------------------------",
        format_metric("Candles Loaded", summary.candles_loaded),
        "------------------------------------------------------------",
        "FINAL CONTEXT DETECTIONS",
        "------------------------------------------------------------",
        format_metric("Market Structure Points", summary.market_structure_points),
        format_metric("BOS Events", summary.bos_events),
        format_metric("CHOCH Events", summary.choch_events),
        format_metric("Liquidity Points", summary.liquidity_points),
        format_metric("Equal High Points", summary.equal_high_points),
        format_metric("Equal Low Points", summary.equal_low_points),
        format_metric("Liquidity Clusters", summary.liquidity_clusters),
        format_metric("Liquidity Sweeps", summary.liquidity_sweeps),
        format_metric("Fair Value Gaps", summary.fair_value_gaps),
        format_metric("Order Blocks", summary.order_blocks),
        "------------------------------------------------------------",
        "WALK-FORWARD STRATEGY",
        "------------------------------------------------------------",
        format_metric("Long Signals", summary.long_signals),
        format_metric("Short Signals", summary.short_signals),
        format_metric("Neutral Signals", summary.neutral_signals),
        format_metric("Trade Candidates", summary.trade_candidates),
        format_metric(
            "Trade Plans Before De-duplication",
            summary.trade_plans_before_deduplication,
        ),
        format_metric(
            "Duplicate Trade Plans Removed",
            summary.duplicate_trade_plans_removed,
        ),
        format_metric(
            "Trade Plans After De-duplication",
            summary.trade_plans_after_deduplication,
        ),
        "------------------------------------------------------------",
        "EXECUTION",
        "------------------------------------------------------------",
        format_metric("Closed Trades", summary.closed_trades),
        format_metric("Total PnL", summary.total_pnl),
        "============================================================",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """
    Run SMC backtest diagnostics and print report.
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

    summary = diagnose(
        csv_path=csv_path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        risk_profile=risk_profile,
        strategy_mode=args.strategy_mode,
    )

    print(build_report(summary))


if __name__ == "__main__":
    main()
