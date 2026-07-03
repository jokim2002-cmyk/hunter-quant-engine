"""
Base Risk Manager Contract

Defines the abstract contract for converting strategy signals into trade plans.
"""

from abc import ABC, abstractmethod

from src.risk.risk_profile import RiskProfile
from src.risk.trade_plan import TradePlan
from src.strategy.trade_signal import TradeSignal


class BaseRiskManager(ABC):
    """
    Base contract for risk managers.

    Risk managers convert strategy signals into risk-approved trade plans.

    Risk managers do not:
    - create strategy signals
    - detect market events
    - execute trades
    - mutate signals or risk profiles
    """

    @abstractmethod
    def plan(
        self,
        signal: TradeSignal,
        risk_profile: RiskProfile,
        entry_price: float,
        stop_loss: float,
    ) -> tuple[TradePlan, ...]:
        """
        Create trade plans from a strategy signal.

        Args:
            signal: Immutable strategy signal.
            risk_profile: Immutable risk profile.
            entry_price: Planned trade entry price.
            stop_loss: Planned stop-loss price.

        Returns:
            Tuple of immutable trade plans.
            Returns an empty tuple when no trade should be planned.
        """
        raise NotImplementedError
