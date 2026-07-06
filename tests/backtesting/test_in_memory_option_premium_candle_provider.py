"""
In-Memory Option Premium Candle Provider Tests
"""

from datetime import date, datetime
from pathlib import Path

import pytest

import src.backtesting.in_memory_option_premium_candle_provider as provider_module
from src.backtesting.in_memory_option_premium_candle_provider import (
    InMemoryOptionPremiumCandleProvider,
)
from src.backtesting.option_buy_backtest_runner import OptionBuyBacktestRunner
from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_chain_snapshot import OptionChainSnapshot
from src.models.option_contract import OptionContract
from src.models.option_premium_candle import OptionPremiumCandle
from src.models.option_type import OptionType
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_build_result import (
    OptionBuyTradePlanBuildResult,
)
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


def _candle(timestamp, close=100.0):
    return OptionPremiumCandle(
        timestamp=timestamp,
        open=close,
        high=close + 5.0,
        low=close - 5.0,
        close=close,
        volume=1000,
    )


def _signal():
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=datetime(2026, 7, 6, 10, 15),
    )


def _contract(symbol="NIFTY26JUL24200CE"):
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol=symbol,
    )


def _entry(symbol="NIFTY26JUL24200CE"):
    return OptionChainEntry(
        contract=_contract(symbol=symbol),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _approved_plan(symbol="NIFTY26JUL24200CE"):
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(symbol=symbol),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=1,
        estimated_charges=10.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )


def _snapshot():
    return OptionChainSnapshot(
        underlying_symbol="NIFTY",
        underlying_price=24210.0,
        timestamp=datetime(2026, 7, 6, 10, 15),
        entries=(_entry(),),
    )


class _ApprovedPlanner:
    def __init__(self, plan):
        self._plan = plan

    def plan(self, signal, snapshot):
        return OptionBuyTradePlanBuildResult(plan=self._plan)


def test_provider_normalizes_candles_to_tuple():
    candle = _candle(datetime(2026, 7, 6, 10, 15))
    provider = InMemoryOptionPremiumCandleProvider({"NIFTY26JUL24200CE": [candle]})

    assert provider.get_candles_for_symbol("NIFTY26JUL24200CE") == (candle,)


def test_provider_sorts_candles_by_timestamp_ascending():
    later = _candle(datetime(2026, 7, 6, 10, 20), close=105.0)
    earlier = _candle(datetime(2026, 7, 6, 10, 15), close=100.0)

    provider = InMemoryOptionPremiumCandleProvider(
        {"NIFTY26JUL24200CE": (later, earlier)}
    )

    assert provider.get_candles_for_symbol("NIFTY26JUL24200CE") == (earlier, later)


def test_provider_rejects_blank_symbol_key():
    with pytest.raises(ValueError, match="option premium candle symbol is required"):
        InMemoryOptionPremiumCandleProvider({" ": (_candle(datetime(2026, 7, 6)),)})


def test_provider_rejects_empty_candle_sequence():
    with pytest.raises(
        ValueError,
        match="option premium candles are required for symbol: NIFTY26JUL24200CE",
    ):
        InMemoryOptionPremiumCandleProvider({"NIFTY26JUL24200CE": ()})


def test_get_candles_returns_candles_for_plan_contract_symbol():
    candle = _candle(datetime(2026, 7, 6, 10, 15))
    provider = InMemoryOptionPremiumCandleProvider({"NIFTY26JUL24200CE": (candle,)})

    assert provider.get_candles(_approved_plan()) == (candle,)


def test_callable_provider_returns_candles_for_plan_contract_symbol():
    candle = _candle(datetime(2026, 7, 6, 10, 15))
    provider = InMemoryOptionPremiumCandleProvider({"NIFTY26JUL24200CE": (candle,)})

    assert provider(_approved_plan()) == (candle,)


def test_get_candles_for_symbol_returns_candles():
    candle = _candle(datetime(2026, 7, 6, 10, 15))
    provider = InMemoryOptionPremiumCandleProvider({"NIFTY26JUL24200CE": (candle,)})

    assert provider.get_candles_for_symbol("NIFTY26JUL24200CE") == (candle,)


def test_get_candles_rejects_missing_plan_contract_symbol():
    candle = _candle(datetime(2026, 7, 6, 10, 15))
    provider = InMemoryOptionPremiumCandleProvider({"NIFTY26JUL24200CE": (candle,)})
    plan = _approved_plan()
    object.__setattr__(plan.entry.contract, "symbol", " ")

    with pytest.raises(
        ValueError,
        match="option contract symbol is required to fetch premium candles",
    ):
        provider.get_candles(plan)


def test_get_candles_rejects_unknown_symbol():
    provider = InMemoryOptionPremiumCandleProvider(
        {"NIFTY26JUL24200CE": (_candle(datetime(2026, 7, 6, 10, 15)),)}
    )

    with pytest.raises(
        ValueError,
        match="option premium candles not found for symbol: UNKNOWN",
    ):
        provider.get_candles(_approved_plan(symbol="UNKNOWN"))


def test_provider_can_be_passed_into_option_buy_backtest_runner():
    plan = _approved_plan()
    candles = (
        _candle(datetime(2026, 7, 6, 10, 15), close=100.0),
        _candle(datetime(2026, 7, 6, 10, 20), close=150.0),
    )
    provider = InMemoryOptionPremiumCandleProvider(
        {"NIFTY26JUL24200CE": candles}
    )

    summary = OptionBuyBacktestRunner(
        planner=_ApprovedPlanner(plan),
    ).run(
        signals=(_signal(),),
        snapshots=(_snapshot(),),
        premium_candle_provider=provider,
    )

    assert summary.completed_trades == 1
    assert summary.failed_backtests == 0


def test_provider_remains_broker_agnostic_and_does_not_import_fyers_modules():
    source = Path(provider_module.__file__).read_text(encoding="utf-8").lower()

    assert "fyers" not in source
