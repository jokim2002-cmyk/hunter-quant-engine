"""
Base Price Fill Model Contract

Defines the abstract contract for price fill models.
"""

from abc import ABC, abstractmethod

from src.backtesting.price_fill_result import PriceFillResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan


class BasePriceFillModel(ABC):
    """
    Base contract for all price fill models.

    Price fill models determine whether a trade plan is filled or closed
    by a single market candle.

    Price fill models do not:
    - iterate candles
    - create trade results
    - calculate performance
    - manage trade lifecycle
    """

    @abstractmethod
    def evaluate(
        self,
        trade_plan: TradePlan,
        candle: Candle,
    ) -> PriceFillResult:
        """
        Evaluate whether a trade plan is filled by a candle.

        Args:
            trade_plan: Immutable trade plan.
            candle: Market candle.

        Returns:
            Immutable price fill result.
        """
        raise NotImplementedError
