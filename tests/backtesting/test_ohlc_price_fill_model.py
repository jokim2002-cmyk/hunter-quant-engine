"""
Tests for OHLCPriceFillModel.
"""

from datetime import datetime

from src.backtesting.ohlc_price_fill_model import OHLCPriceFillModel
from src.backtesting.price_fill_result import PriceFillResult
from src.models.candle import Candle
from src.risk.trade_plan import TradePlan
from src.strategy.signal_type import SignalType


def _candle(high: float, low: float) -> Candle:
    return Candle(
        datetime=datetime(2026, 1, 1, 10, 0),
        open=100.0,
        high=high,
        low=low,
        close=100.0,
        volume=1000.0,
    )


def _long_trade_plan() -> TradePlan:
    return TradePlan(
        signal_type=SignalType.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size=10.0,
        risk_amount=50.0,
        reward_amount=100.0,
        created_at=datetime(2026, 1, 1, 9, 0),
    )


def _short_trade_plan() -> TradePlan:
    return TradePlan(
        signal_type=SignalType.SHORT,
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        position_size=10.0,
        risk_amount=50.0,
        reward_amount=100.0,
        created_at=datetime(2026, 1, 1, 9, 0),
    )


def test_long_trade_is_not_filled_when_no_level_is_touched():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_long_trade_plan(),
        candle=_candle(high=109.0, low=96.0),
    )

    assert result == PriceFillResult(
        filled=False,
        fill_price=None,
        reason=None,
    )


def test_long_trade_fills_take_profit_when_high_reaches_take_profit():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_long_trade_plan(),
        candle=_candle(high=110.0, low=96.0),
    )

    assert result == PriceFillResult(
        filled=True,
        fill_price=110.0,
        reason="take_profit",
    )


def test_long_trade_fills_stop_loss_when_low_reaches_stop_loss():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_long_trade_plan(),
        candle=_candle(high=109.0, low=95.0),
    )

    assert result == PriceFillResult(
        filled=True,
        fill_price=95.0,
        reason="stop_loss",
    )


def test_long_trade_uses_stop_loss_when_both_levels_are_touched():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_long_trade_plan(),
        candle=_candle(high=110.0, low=95.0),
    )

    assert result == PriceFillResult(
        filled=True,
        fill_price=95.0,
        reason="stop_loss",
    )


def test_short_trade_is_not_filled_when_no_level_is_touched():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_short_trade_plan(),
        candle=_candle(high=104.0, low=91.0),
    )

    assert result == PriceFillResult(
        filled=False,
        fill_price=None,
        reason=None,
    )


def test_short_trade_fills_take_profit_when_low_reaches_take_profit():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_short_trade_plan(),
        candle=_candle(high=104.0, low=90.0),
    )

    assert result == PriceFillResult(
        filled=True,
        fill_price=90.0,
        reason="take_profit",
    )


def test_short_trade_fills_stop_loss_when_high_reaches_stop_loss():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_short_trade_plan(),
        candle=_candle(high=105.0, low=91.0),
    )

    assert result == PriceFillResult(
        filled=True,
        fill_price=105.0,
        reason="stop_loss",
    )


def test_short_trade_uses_stop_loss_when_both_levels_are_touched():
    result = OHLCPriceFillModel().evaluate(
        trade_plan=_short_trade_plan(),
        candle=_candle(high=105.0, low=90.0),
    )

    assert result == PriceFillResult(
        filled=True,
        fill_price=105.0,
        reason="stop_loss",
    )
