"""
Option Premium Backtester Exit Slippage Tests
"""

from datetime import date, datetime

import pytest

from src.backtesting.option_premium_backtest_exit_reason import (
    OptionPremiumBacktestExitReason,
)
from src.backtesting.option_premium_backtester import OptionPremiumBacktester
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
        rationale=("exit slippage test",),
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
        ask_price=100.0,
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
        estimated_charges=0.0,
        status=OptionBuyTradePlanStatus.APPROVED,
    )


def _candle(
    low=95.0,
    high=105.0,
    close=100.0,
):
    return OptionPremiumCandle(
        timestamp=datetime(2026, 7, 6, 10, 20),
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def test_default_exit_slippage_keeps_legacy_target_exit_premium():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=170.0),),
    )

    assert result.exit_reason is OptionPremiumBacktestExitReason.TARGET_HIT
    assert result.exit_premium == pytest.approx(160.0)


def test_exit_slippage_reduces_target_exit_premium():
    result = OptionPremiumBacktester(exit_slippage_percent=0.01).backtest(
        plan=_plan(),
        premium_candles=(_candle(high=170.0),),
    )

    assert result.exit_reason is OptionPremiumBacktestExitReason.TARGET_HIT
    assert result.exit_premium == pytest.approx(158.4)


def test_exit_slippage_reduces_stop_loss_exit_premium():
    result = OptionPremiumBacktester(exit_slippage_percent=0.01).backtest(
        plan=_plan(),
        premium_candles=(_candle(low=60.0),),
    )

    assert result.exit_reason is OptionPremiumBacktestExitReason.STOP_LOSS_HIT
    assert result.exit_premium == pytest.approx(69.3)


def test_exit_slippage_reduces_end_of_data_exit_premium():
    result = OptionPremiumBacktester(exit_slippage_percent=0.01).backtest(
        plan=_plan(),
        premium_candles=(_candle(close=100.0),),
    )

    assert result.exit_reason is OptionPremiumBacktestExitReason.END_OF_DATA
    assert result.exit_premium == pytest.approx(99.0)


def test_exit_slippage_cannot_be_negative():
    with pytest.raises(ValueError, match="exit_slippage_percent cannot be negative"):
        OptionPremiumBacktester(exit_slippage_percent=-0.01)
