"""
Base Trade Execution Simulator Contract

Defines the abstract contract for simulating historical trade execution.
"""

from abc import ABC, abstractmethod

from src.backtesting.trade_result import TradeResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan


class BaseTradeExecutionSimulator(ABC):
    """
    Base contract for historical trade execution simulators.

    Execution simulators convert trade plans and future candles into
    completed historical trade results.
    """

    @abstractmethod
    def simulate(
        self,
        trade_plan: TradePlan,
        candles: tuple[Candle, ...],
    ) -> TradeResult | None:
        """
        Simulate execution of a trade plan over future candles.

        Returns:
            TradeResult when the trade closes, otherwise None.
        """
        raise NotImplementedError
