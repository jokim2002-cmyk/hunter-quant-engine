"""
Trade Plan Deduplicator

Filters duplicate trade plans before historical execution.
"""

from src.backtesting.base_trade_plan_deduplicator import (
    BaseTradePlanDeduplicator,
)
from src.risk.trade_plan import TradePlan


class TradePlanDeduplicator(BaseTradePlanDeduplicator):
    """
    Default trade plan de-duplicator.

    Two trade plans are treated as duplicates when they have the same:
    - signal type
    - entry price
    - stop loss
    - take profit

    created_at is intentionally ignored so the same setup does not generate
    repeated trades on consecutive candles.
    """

    def __init__(
        self,
        price_precision: int = 9,
    ):
        self._price_precision = price_precision

    def deduplicate(
        self,
        trade_plans: tuple[TradePlan, ...],
    ) -> tuple[TradePlan, ...]:
        """
        Remove duplicate trade plans while preserving first occurrence order.

        Args:
            trade_plans: Risk-approved trade plans.

        Returns:
            De-duplicated trade plans.
        """
        unique_trade_plans: list[TradePlan] = []
        seen_keys = set()

        for trade_plan in trade_plans:
            key = self._key(trade_plan)

            if key in seen_keys:
                continue

            seen_keys.add(key)
            unique_trade_plans.append(trade_plan)

        return tuple(unique_trade_plans)

    def _key(
        self,
        trade_plan: TradePlan,
    ) -> tuple:
        return (
            trade_plan.signal_type,
            self._normalize_price(trade_plan.entry_price),
            self._normalize_price(trade_plan.stop_loss),
            self._normalize_price(trade_plan.take_profit),
        )

    def _normalize_price(
        self,
        price: float,
    ) -> float:
        return round(price, self._price_precision)
