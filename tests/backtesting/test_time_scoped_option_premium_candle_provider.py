"""
Time-Scoped Option Premium Candle Provider Tests
"""

from datetime import date, datetime

import pytest

from src.backtesting.time_scoped_option_premium_candle_provider import (
    TimeScopedOptionPremiumCandleProvider,
)
from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


def _signal():
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("time-scope test",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _entry():
    return OptionChainEntry(
        contract=OptionContract(
            underlying_symbol="NIFTY",
            expiry_date=date(2026, 7, 9),
            strike_price=24200.0,
            option_type=OptionType.CE,
            lot_size=65,
            symbol="NIFTY26JUL24200CE",
        ),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _plan():
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=1,
        estimated_charges=10.0,
        status=OptionBuyTradePlanStatus.APPROVED,
    )


def _candle(timestamp, close=100.0):
    return OptionPremiumCandle(
        timestamp=timestamp,
        open=close,
        high=close + 5.0,
        low=close - 5.0,
        close=close,
        volume=1000,
    )


def test_provider_filters_candles_before_signal_time():
    old_candle = _candle(datetime(2026, 7, 6, 10, 10), close=90.0)
    signal_candle = _candle(datetime(2026, 7, 6, 10, 15), close=100.0)
    future_candle = _candle(datetime(2026, 7, 6, 10, 20), close=110.0)

    provider = TimeScopedOptionPremiumCandleProvider(
        delegate=lambda plan: (old_candle, signal_candle, future_candle)
    )

    assert provider(_plan()) == (signal_candle, future_candle)


def test_provider_caps_max_bars_held_after_signal_time():
    signal_candle = _candle(datetime(2026, 7, 6, 10, 15), close=100.0)
    future_candle = _candle(datetime(2026, 7, 6, 10, 20), close=110.0)

    provider = TimeScopedOptionPremiumCandleProvider(
        delegate=lambda plan: (signal_candle, future_candle),
        max_bars_held=1,
    )

    assert provider(_plan()) == (signal_candle,)


def test_provider_rejects_non_positive_max_bars_held():
    with pytest.raises(ValueError, match="max_bars_held must be greater than 0"):
        TimeScopedOptionPremiumCandleProvider(
            delegate=lambda plan: (),
            max_bars_held=0,
        )


def test_provider_raises_clear_error_when_no_candles_remain_after_filter():
    old_candle = _candle(datetime(2026, 7, 6, 10, 10), close=90.0)
    provider = TimeScopedOptionPremiumCandleProvider(
        delegate=lambda plan: (old_candle,)
    )

    with pytest.raises(
        ValueError,
        match="time-scoped option premium candles not found for symbol",
    ):
        provider(_plan())
