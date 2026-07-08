"""
Time-Scoped Option Premium Candle Provider

Filters option premium candles so offline option-buy replay only sees candles
at or after the plan signal time. This prevents historical candles before the
signal from affecting backtest exits.
"""

from collections.abc import Callable, Sequence

from src.models.option_premium_candle import OptionPremiumCandle
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan


class TimeScopedOptionPremiumCandleProvider:
    """
    Wraps an option premium candle provider with signal-time replay controls.
    """

    def __init__(
        self,
        delegate: Callable[[OptionBuyTradePlan], Sequence[OptionPremiumCandle]],
        max_bars_held: int | None = None,
    ):
        """
        Initialize the wrapper.

        Args:
            delegate: Existing premium candle provider.
            max_bars_held: Optional maximum number of bars to replay after signal time.
        """
        if max_bars_held is not None and max_bars_held <= 0:
            raise ValueError("max_bars_held must be greater than 0 when provided")

        self.delegate = delegate
        self.max_bars_held = max_bars_held

    def __call__(
        self,
        plan: OptionBuyTradePlan,
    ) -> tuple[OptionPremiumCandle, ...]:
        """
        Return candles at or after the plan signal time, optionally capped.
        """
        all_candles = tuple(self.delegate(plan))
        scoped_candles = tuple(
            candle
            for candle in all_candles
            if candle.timestamp >= plan.signal.created_at
        )

        if self.max_bars_held is not None:
            scoped_candles = scoped_candles[: self.max_bars_held]

        if not scoped_candles:
            symbol = plan.entry.contract.symbol
            raise ValueError(
                "time-scoped option premium candles not found for symbol: "
                f"{symbol}"
            )

        return scoped_candles
