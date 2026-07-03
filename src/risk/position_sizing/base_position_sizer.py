"""
Base Position Sizer Contract

Defines the abstract contract for position sizing algorithms.
"""

from abc import ABC, abstractmethod

from src.risk.risk_profile import RiskProfile


class BasePositionSizer(ABC):
    """
    Base contract for all position sizing algorithms.

    Position sizers calculate trade size from risk configuration
    and price risk.

    Position sizers do not:
    - create trade signals
    - create trade plans
    - execute trades
    - mutate risk profiles
    """

    @abstractmethod
    def calculate(
        self,
        risk_profile: RiskProfile,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        """
        Calculate position size.

        Args:
            risk_profile: Immutable risk profile.
            entry_price: Planned trade entry price.
            stop_loss: Planned stop-loss price.

        Returns:
            Position size.
        """
        raise NotImplementedError
