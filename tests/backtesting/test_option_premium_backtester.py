"""
Option Premium Backtester Tests
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
        rationale=("test signal",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _contract():
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol="NIFTY26JUL24200CE",
    )


def _entry():
    return OptionChainEntry(
        contract=_contract(),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _plan(status=OptionBuyTradePlanStatus.APPROVED):
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=2,
        estimated_charges=40.0,
        status=status,
        rejection_reasons=(
            ("setup rejected",)
            if status is OptionBuyTradePlanStatus.REJECTED
            else ()
        ),
    )


def _candle(open_price=100.0, high=110.0, low=90.0, close=105.0, volume=1000):
    return OptionPremiumCandle(
        timestamp=datetime(2026, 7, 6, 10, 15),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_option_premium_candle_validates_ohlc_values():
    candle = _candle()

    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 90.0
    assert candle.close == 105.0
    assert candle.volume == 1000


@pytest.mark.parametrize("field_name", ("open", "high", "low", "close"))
def test_option_premium_candle_rejects_non_positive_prices(field_name):
    values = {
        "open_price": 100.0,
        "high": 110.0,
        "low": 90.0,
        "close": 105.0,
    }
    key = "open_price" if field_name == "open" else field_name
    values[key] = 0

    with pytest.raises(ValueError, match=f"{field_name} must be greater than 0"):
        _candle(**values)


def test_option_premium_candle_rejects_invalid_high():
    with pytest.raises(
        ValueError,
        match="high must be greater than or equal to open, close, and low",
    ):
        _candle(open_price=100.0, high=99.0, low=90.0, close=105.0)


def test_option_premium_candle_rejects_invalid_low():
    with pytest.raises(
        ValueError,
        match="low must be less than or equal to open, close, and high",
    ):
        _candle(open_price=100.0, high=110.0, low=106.0, close=105.0)


def test_option_premium_candle_rejects_negative_volume():
    with pytest.raises(ValueError, match="volume must be greater than or equal to 0"):
        _candle(volume=-1)


def test_backtester_rejects_rejected_non_approved_plan():
    with pytest.raises(
        ValueError,
        match="only approved option-buy trade plans can be backtested",
    ):
        OptionPremiumBacktester().backtest(
            plan=_plan(status=OptionBuyTradePlanStatus.REJECTED),
            premium_candles=(_candle(),),
        )


def test_backtester_rejects_empty_candles():
    with pytest.raises(ValueError, match="premium candles are required"):
        OptionPremiumBacktester().backtest(
            plan=_plan(),
            premium_candles=(),
        )


def test_backtester_exits_at_stop_loss_when_low_hits_sl():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=120.0, low=69.0),),
    )

    assert result.exit_reason == OptionPremiumBacktestExitReason.STOP_LOSS_HIT
    assert result.exit_premium == 70.0


def test_backtester_exits_at_target_when_high_hits_target():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.exit_reason == OptionPremiumBacktestExitReason.TARGET_HIT
    assert result.exit_premium == 160.0


def test_stop_loss_wins_when_sl_and_target_both_hit_in_same_candle():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=69.0),),
    )

    assert result.exit_reason == OptionPremiumBacktestExitReason.STOP_LOSS_HIT
    assert result.exit_premium == 70.0


def test_backtester_exits_at_last_close_when_end_of_data():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(
            _candle(high=120.0, low=90.0, close=110.0),
            _candle(high=130.0, low=95.0, close=125.0),
        ),
    )

    assert result.exit_reason == OptionPremiumBacktestExitReason.END_OF_DATA
    assert result.exit_premium == 125.0
    assert result.bars_held == 2


def test_result_calculates_quantity():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.quantity == 130


def test_result_calculates_gross_pnl():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.gross_pnl == 7800.0


def test_result_calculates_net_pnl():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.net_pnl == 7760.0


def test_result_calculates_is_win():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.is_win is True


def test_result_calculates_is_loss():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=120.0, low=69.0),),
    )

    assert result.is_loss is True


def test_result_calculates_return_percent():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.return_percent == 0.6


def test_bars_held_is_correct_for_target_on_second_candle():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(
            _candle(high=120.0, low=90.0),
            _candle(high=161.0, low=95.0),
        ),
    )

    assert result.exit_reason == OptionPremiumBacktestExitReason.TARGET_HIT
    assert result.bars_held == 2


def test_estimated_charges_is_copied_from_plan():
    result = OptionPremiumBacktester().backtest(
        plan=_plan(),
        premium_candles=(_candle(high=161.0, low=90.0),),
    )

    assert result.estimated_charges == 40.0
