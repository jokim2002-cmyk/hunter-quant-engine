"""
Base Strategy Context Factory Contract

Defines the abstract contract for building StrategyContext snapshots.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from src.models.candle import Candle
from src.strategy.strategy_context import StrategyContext


class BaseStrategyContextFactory(ABC):
    """
    Base contract for strategy context factories.

    Strategy context factories build immutable StrategyContext snapshots
    from walk-forward candle data.

    Strategy context factories do not:
    - create trade signals
    - create trade plans
    - calculate risk
    - execute backtests
    """

    @abstractmethod
    def create(
        self,
        symbol: str,
        timeframe: str,
        analysis_time: datetime,
        candles: tuple[Candle, ...],
    ) -> StrategyContext:
        """
        Create a StrategyContext snapshot.

        Args:
            symbol: Market symbol.
            timeframe: Market timeframe.
            analysis_time: Current analysis timestamp.
            candles: Walk-forward candles available at analysis time.

        Returns:
            Immutable StrategyContext.
        """
        raise NotImplementedError
