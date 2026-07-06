"""
Option Buy Plan to Paper Order Adapter Tests

Fake/local paper trading adapter only. No real orders. No live market data.
Not a profitability claim.
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.paper_trading.option_buy_plan_to_paper_order import (
    create_paper_order_request_from_option_buy_plan,
)
from src.paper_trading.paper_order_journal import PaperOrderRequest, PaperOrderStatus
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus

_TS = datetime(2026, 7, 6, 9, 15)


def _signal():
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=_TS,
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


def _approved_plan(**overrides):
    values = dict(
        signal=_signal(),
        entry=_entry(),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=100.0,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=2,
        estimated_charges=40.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )
    values.update(overrides)
    return OptionBuyTradePlan(**values)


def _rejected_plan():
    return _approved_plan(
        status=OptionBuyTradePlanStatus.REJECTED,
        rejection_reasons=("plan rejected",),
    )


def test_valid_option_buy_trade_plan_converts_to_paper_order_request():
    request = create_paper_order_request_from_option_buy_plan(_approved_plan())

    assert isinstance(request, PaperOrderRequest)
    assert request.symbol == "NIFTY26JUL24200CE"
    assert request.quantity == 130
    assert request.planned_entry_price == 100.0
    assert request.created_at == _TS


def test_symbol_is_copied_correctly():
    request = create_paper_order_request_from_option_buy_plan(
        _approved_plan(entry=_entry(symbol="NIFTY26JUL24200CE"))
    )

    assert request.symbol == "NIFTY26JUL24200CE"


def test_quantity_is_copied_from_trade_plan():
    request = create_paper_order_request_from_option_buy_plan(_approved_plan(lots=3))

    assert request.quantity == 195


def test_planned_entry_price_is_copied_correctly():
    request = create_paper_order_request_from_option_buy_plan(
        _approved_plan(entry_premium=112.5)
    )

    assert request.planned_entry_price == 112.5


def test_buy_only_fake_local_behavior_is_preserved():
    request = create_paper_order_request_from_option_buy_plan(_approved_plan())

    assert isinstance(request, PaperOrderRequest)
    assert not hasattr(request, "side")
    assert request.quantity > 0
    assert request.planned_entry_price > 0


def test_plan_id_is_preserved_when_supported():
    plan = _approved_plan()
    object.__setattr__(plan, "plan_id", "plan-123")

    request = create_paper_order_request_from_option_buy_plan(plan)

    assert request.plan_id == "plan-123"


def test_converted_request_can_be_submitted_to_paper_trading_session():
    session = PaperTradingSession()
    request = create_paper_order_request_from_option_buy_plan(_approved_plan())

    record = session.submit_order(request)

    assert record.order_id == "PAPER-000001"
    assert record.status is PaperOrderStatus.OPEN


def test_converted_request_opens_or_updates_paper_position_state():
    session = PaperTradingSession()
    request_one = create_paper_order_request_from_option_buy_plan(_approved_plan())
    request_two = create_paper_order_request_from_option_buy_plan(
        _approved_plan(lots=1, entry_premium=120.0)
    )

    session.submit_order(request_one)
    session.submit_order(request_two)

    position = session.find_position("NIFTY26JUL24200CE")
    assert position is not None
    assert position.quantity == 195
    assert position.average_entry_price == pytest.approx(106.6666666667)


def test_converted_request_can_be_submitted_and_recorded():
    session = PaperTradingSession()
    request = create_paper_order_request_from_option_buy_plan(_approved_plan())

    record = session.submit_order(request)

    assert record.order_id == "PAPER-000001"
    assert session.find_order(record.order_id) is record


def test_invalid_rejected_plan_raises_value_error():
    with pytest.raises(
        ValueError,
        match="only approved option-buy trade plans can be converted",
    ):
        create_paper_order_request_from_option_buy_plan(_rejected_plan())


def test_missing_blank_symbol_raises_value_error():
    with pytest.raises(ValueError, match="symbol is required"):
        _entry(symbol=" ")


def test_zero_quantity_raises_value_error():
    plan = _approved_plan(lots=1)
    object.__setattr__(plan.entry.contract, "lot_size", 0)

    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        create_paper_order_request_from_option_buy_plan(plan)


def test_negative_quantity_raises_value_error():
    plan = _approved_plan(lots=1)
    object.__setattr__(plan.entry.contract, "lot_size", -1)

    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        create_paper_order_request_from_option_buy_plan(plan)


def test_zero_entry_price_raises_value_error():
    with pytest.raises(ValueError, match="entry_premium must be greater than 0"):
        _approved_plan(entry_premium=0.0)


def test_negative_entry_price_raises_value_error():
    with pytest.raises(ValueError, match="entry_premium must be greater than 0"):
        _approved_plan(entry_premium=-5.0)


def test_no_broker_or_fyers_string_appears_in_new_production_file():
    source = Path("src/paper_trading/option_buy_plan_to_paper_order.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "fyers" not in source


def test_no_real_order_placement_method_exists():
    source = Path("src/paper_trading/option_buy_plan_to_paper_order.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "place_order" not in source
    assert "send_order" not in source
    assert "execute_order" not in source
