"""
Option Buy Backtest Scenario Builder

Builds broker-agnostic option-buy backtest scenarios from signals and snapshots.
"""

from collections.abc import Sequence
from typing import TypeVar

from src.backtesting.option_buy_backtest_scenario import OptionBuyBacktestScenario
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.strategy.trade_signal import TradeSignal


T = TypeVar("T")


class OptionBuyBacktestScenarioBuilder:
    """
    Pair TradeSignal objects with OptionChainSnapshot objects in order.
    """

    def build_scenarios(
        self,
        signals: Sequence[TradeSignal],
        snapshots: Sequence[OptionChainSnapshot],
    ) -> tuple[OptionBuyBacktestScenario, ...]:
        """
        Create one scenario for each signal/snapshot pair.
        """
        if not signals:
            raise ValueError("signals are required")

        if not snapshots:
            raise ValueError("snapshots are required")

        if len(signals) != len(snapshots):
            raise ValueError("signals and snapshots must have the same length")

        return tuple(
            OptionBuyBacktestScenario(signal=signal, snapshot=snapshot)
            for signal, snapshot in zip(signals, snapshots)
        )

    def split_scenarios(
        self,
        scenarios: Sequence[OptionBuyBacktestScenario],
    ) -> tuple[tuple[TradeSignal, ...], tuple[OptionChainSnapshot, ...]]:
        """
        Split scenarios back into signals and snapshots while preserving order.
        """
        if not scenarios:
            raise ValueError("option buy backtest scenarios are required")

        signals = tuple(scenario.signal for scenario in scenarios)
        snapshots = tuple(scenario.snapshot for scenario in scenarios)
        return signals, snapshots
