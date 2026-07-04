"""
Base Trade Plan Deduplicator Contract

Defines the abstract contract for filtering duplicate trade plans.
"""

from abc import ABC, abstractmethod

from src.risk.trade_plan import TradePlan


class BaseTradePlanDeduplicator(ABC):
    """
    Base contract for trade plan de-duplication.

    Trade plan de-duplicators remove repeated execution plans without changing
    strategy, candidate planning, risk management, or trade execution behavior.
    """

    @abstractmethod
    def deduplicate(
        self,
        trade_plans: tuple[TradePlan, ...],
    ) -> tuple[TradePlan, ...]:
        """
        Remove duplicate trade plans.

        Args:
            trade_plans: Risk-approved trade plans.

        Returns:
            De-duplicated trade plans.
        """
        raise NotImplementedError
