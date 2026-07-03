"""
Base Trade Level Planner Contract

Defines the abstract contract for trade level planning.
"""

from abc import ABC, abstractmethod

from src.risk.risk_profile import RiskProfile
from src.risk.trade_level_planning.trade_levels import TradeLevels
from src.strategy.signal_type import SignalType


class BaseTradeLevelPlanner(ABC):
    """
    Base contract for all trade level planners.

    Trade level planners calculate price levels from strategy direction,
    entry price, stop-loss price, and risk configuration.

    Trade level planners do not:
    - create trade signals
    - calculate position size
    - create trade plans
    - execute trades
    """

    @abstractmethod
    def plan(
        self,
        signal_type: SignalType,
        entry_price: float,
        stop_loss: float,
        risk_profile: RiskProfile,
    ) -> TradeLevels:
        """
        Plan trade price levels.

        Args:
            signal_type: Directional strategy signal type.
            entry_price: Planned trade entry price.
            stop_loss: Planned stop-loss price.
            risk_profile: Immutable risk profile.

        Returns:
            Immutable trade levels.
        """
        raise NotImplementedError
