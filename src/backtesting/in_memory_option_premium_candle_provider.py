"""
In-Memory Option Premium Candle Provider

Broker-agnostic provider for supplied option premium candles.
"""

from collections.abc import Mapping, Sequence

from src.models.option_premium_candle import OptionPremiumCandle
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan


class InMemoryOptionPremiumCandleProvider:
    """
    Provides option premium candles from an in-memory symbol map.
    """

    def __init__(
        self,
        candle_data_by_symbol: Mapping[str, Sequence[OptionPremiumCandle]],
    ):
        """
        Normalize supplied candle data by option contract symbol.
        """
        self._candle_data_by_symbol = {}

        for symbol, candles in candle_data_by_symbol.items():
            if not symbol.strip():
                raise ValueError("option premium candle symbol is required")

            normalized_candles = tuple(candles)
            if not normalized_candles:
                raise ValueError(
                    f"option premium candles are required for symbol: {symbol}"
                )

            self._candle_data_by_symbol[symbol] = tuple(
                sorted(normalized_candles, key=lambda candle: candle.timestamp)
            )

    def get_candles(
        self,
        plan: OptionBuyTradePlan,
    ) -> tuple[OptionPremiumCandle, ...]:
        """
        Return premium candles for the option contract in a plan.
        """
        symbol = plan.entry.contract.symbol
        if not symbol.strip():
            raise ValueError("option contract symbol is required to fetch premium candles")

        return self.get_candles_for_symbol(symbol)

    def __call__(
        self,
        plan: OptionBuyTradePlan,
    ) -> tuple[OptionPremiumCandle, ...]:
        """
        Delegate callable provider use to get_candles.
        """
        return self.get_candles(plan)

    def get_candles_for_symbol(
        self,
        symbol: str,
    ) -> tuple[OptionPremiumCandle, ...]:
        """
        Return premium candles for a specific option contract symbol.
        """
        if not symbol.strip():
            raise ValueError("option premium candle symbol is required")

        if symbol not in self._candle_data_by_symbol:
            raise ValueError(f"option premium candles not found for symbol: {symbol}")

        return self._candle_data_by_symbol[symbol]
