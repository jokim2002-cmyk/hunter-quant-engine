"""
OHLC Price Fill Model

Determines stop-loss and take-profit fills using OHLC candle data.
"""

from src.backtesting.base_price_fill_model import BasePriceFillModel
from src.backtesting.price_fill_result import PriceFillResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


class OHLCPriceFillModel(BasePriceFillModel):
    """
    Price fill model for OHLC candles.

    Conservative rule:
    If stop-loss and take-profit are both touched in the same candle,
    stop-loss is assumed to fill first.
    """

    STOP_LOSS_REASON = "stop_loss"
    TAKE_PROFIT_REASON = "take_profit"

    def evaluate(
        self,
        trade_plan: TradePlan,
        candle: Candle,
    ) -> PriceFillResult:
        if trade_plan.signal_type == SignalType.LONG:
            return self._evaluate_long(trade_plan, candle)

        if trade_plan.signal_type == SignalType.SHORT:
            return self._evaluate_short(trade_plan, candle)

        return self._not_filled()

    def _evaluate_long(
        self,
        trade_plan: TradePlan,
        candle: Candle,
    ) -> PriceFillResult:
        stop_loss_hit = candle.low <= trade_plan.stop_loss
        take_profit_hit = candle.high >= trade_plan.take_profit

        if stop_loss_hit:
            return PriceFillResult(
                filled=True,
                fill_price=trade_plan.stop_loss,
                reason=self.STOP_LOSS_REASON,
            )

        if take_profit_hit:
            return PriceFillResult(
                filled=True,
                fill_price=trade_plan.take_profit,
                reason=self.TAKE_PROFIT_REASON,
            )

        return self._not_filled()

    def _evaluate_short(
        self,
        trade_plan: TradePlan,
        candle: Candle,
    ) -> PriceFillResult:
        stop_loss_hit = candle.high >= trade_plan.stop_loss
        take_profit_hit = candle.low <= trade_plan.take_profit

        if stop_loss_hit:
            return PriceFillResult(
                filled=True,
                fill_price=trade_plan.stop_loss,
                reason=self.STOP_LOSS_REASON,
            )

        if take_profit_hit:
            return PriceFillResult(
                filled=True,
                fill_price=trade_plan.take_profit,
                reason=self.TAKE_PROFIT_REASON,
            )

        return self._not_filled()

    def _not_filled(self) -> PriceFillResult:
        return PriceFillResult(
            filled=False,
            fill_price=None,
            reason=None,
        )
