"""
Base Strategy

Defines the abstract contract for all HQE strategies.
"""

from abc import ABC, abstractmethod
from typing import Tuple

from src.strategy.strategy_context import StrategyContext
from src.strategy.trade_signal import TradeSignal


class BaseStrategy(ABC):
    """
    Base contract for all HQE strategies.

    Strategies analyze a StrategyContext and produce one or more
    immutable TradeSignal objects.
    """

    @abstractmethod
    def generate(
        self,
        context: StrategyContext,
    ) -> Tuple[TradeSignal, ...]:
        """
        Generate strategy signals from a market snapshot.
        """
        raise NotImplementedError
