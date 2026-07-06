"""
Option Buy Backtest Runner

Runs supplied signals, snapshots, and premium candles through option-buy backtests.
"""

from collections.abc import Callable, Sequence

from src.backtesting.option_buy_backtest_summary import OptionBuyBacktestSummary
from src.backtesting.option_premium_backtester import OptionPremiumBacktester
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_premium_candle import OptionPremiumCandle
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_planner import OptionBuyPlanner
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan


class OptionBuyBacktestRunner:
    """
    Plans and backtests option-buy trades from supplied data.
    """

    def __init__(
        self,
        planner: OptionBuyPlanner | None = None,
        premium_backtester: OptionPremiumBacktester | None = None,
    ):
        """
        Initialize runner dependencies.
        """
        self.planner = planner or OptionBuyPlanner()
        self.premium_backtester = premium_backtester or OptionPremiumBacktester()

    def run(
        self,
        signals: Sequence[TradeSignal],
        snapshots: Sequence[OptionChainSnapshot],
        premium_candle_provider: Callable[
            [OptionBuyTradePlan],
            Sequence[OptionPremiumCandle],
        ],
    ) -> OptionBuyBacktestSummary:
        """
        Run supplied signals and snapshots through the option-buy backtest flow.
        """
        if not signals:
            raise ValueError("signals are required")

        if not snapshots:
            raise ValueError("snapshots are required")

        if len(signals) != len(snapshots):
            raise ValueError("signals and snapshots must have the same length")

        rejected_plans = 0
        failed_backtests = 0
        results = []
        rejection_reasons = []

        for signal, snapshot in zip(signals, snapshots):
            build_result = self.planner.plan(signal, snapshot)
            if not build_result.has_plan:
                rejected_plans += 1
                rejection_reasons.extend(build_result.rejection_reasons)
                continue

            plan = build_result.plan
            try:
                premium_candles = premium_candle_provider(plan)
                result = self.premium_backtester.backtest(plan, premium_candles)
            except ValueError as error:
                failed_backtests += 1
                rejection_reasons.append(f"option premium backtest failed: {error}")
                continue

            results.append(result)

        return OptionBuyBacktestSummary(
            planned_signals=len(signals),
            rejected_plans=rejected_plans,
            failed_backtests=failed_backtests,
            results=tuple(results),
            rejection_reasons=tuple(rejection_reasons),
        )
