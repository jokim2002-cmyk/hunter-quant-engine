"""
Option Buy Backtest Scenario

Pairs a strategy signal with one option chain snapshot for offline backtesting.
"""

from dataclasses import dataclass

from src.models.option_chain_snapshot import OptionChainSnapshot
from src.strategy.trade_signal import TradeSignal


@dataclass(frozen=True)
class OptionBuyBacktestScenario:
    """
    Represents one option-buy backtest planning scenario.
    """

    signal: TradeSignal
    snapshot: OptionChainSnapshot

    def __post_init__(self):
        """
        Validate scenario fields.
        """
        if self.signal is None:
            raise ValueError("signal is required")

        if self.snapshot is None:
            raise ValueError("snapshot is required")
