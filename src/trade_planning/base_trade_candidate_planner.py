"""
Base Trade Candidate Planner Contract

Defines the abstract contract for converting strategy signals into trade candidates.
"""

from abc import ABC, abstractmethod

from src.strategy.strategy_context import StrategyContext
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.trade_candidate import TradeCandidate


class BaseTradeCandidatePlanner(ABC):
    """
    Base contract for trade candidate planners.

    Trade candidate planners convert strategy signals and market context
    into executable entry and stop-loss levels.

    Trade candidate planners do not:
    - create strategy signals
    - calculate position size
    - calculate take profit
    - execute trades
    - mutate context or signals
    """

    @abstractmethod
    def plan(
        self,
        signal: TradeSignal,
        context: StrategyContext,
    ) -> tuple[TradeCandidate, ...]:
        """
        Create trade candidates from a strategy signal and market context.

        Args:
            signal: Immutable strategy signal.
            context: Immutable strategy context.

        Returns:
            Tuple of immutable trade candidates.
            Returns an empty tuple when no trade candidate should be created.
        """
        raise NotImplementedError
