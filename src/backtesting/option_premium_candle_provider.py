"""
Option Premium Candle Provider

Broker-agnostic interface for fetching option premium candles for a plan.
"""

from collections.abc import Sequence
from typing import Protocol

from src.models.option_premium_candle import OptionPremiumCandle
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan


class OptionPremiumCandleProvider(Protocol):
    """
    Protocol for option premium candle providers.
    """

    def get_candles(
        self,
        plan: OptionBuyTradePlan,
    ) -> Sequence[OptionPremiumCandle]:
        """
        Return premium candles for an option-buy trade plan.
        """

    def __call__(
        self,
        plan: OptionBuyTradePlan,
    ) -> Sequence[OptionPremiumCandle]:
        """
        Return premium candles for an option-buy trade plan.
        """
