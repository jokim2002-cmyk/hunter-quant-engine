"""
Paper trading workflow smoke tests.

Fake/local only: OptionBuyTradePlan -> PaperOrderRequest -> PaperTradingSession
-> PaperOrderRecord -> PaperPosition.

No broker integration and no real order placement.

"""

from __future__ import annotations

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
from src.paper_trading.paper_order_journal import PaperOrderStatus
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_position_state import PaperPosition
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


_TS = datetime(2026, 7, 6, 9, 15)


def _signal() -> TradeSignal:
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("test signal",),
        created_at=_TS,
    )


def _contract(symbol: str) -> OptionContract:
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol=symbol,
    )


def _entry(symbol: str) -> OptionChainEntry:
    return OptionChainEntry(
        contract=_contract(symbol=symbol),
        last_traded_price=100.0,
        bid_price=99.0,
        ask_price=101.0,
        volume=10000,
        open_interest=50000,
    )


def _approved_plan(*, symbol: str, lots: int, entry_premium: float) -> OptionBuyTradePlan:
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(symbol=symbol),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=entry_premium,
        stop_loss_premium=70.0,
        target_premium=160.0,
        lots=lots,
        estimated_charges=40.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )


def test_option_buy_plan_to_paper_session_workflow_smoke_test_opens_position_and_records_order():
    session = PaperTradingSession()

    symbol = "NIFTY26JUL24200CE"
    lots = 2
    entry_premium = 100.0

    plan = _approved_plan(symbol=symbol, lots=lots, entry_premium=entry_premium)

    request = create_paper_order_request_from_option_buy_plan(plan)

    record = session.submit_order(request)

    # Assert PaperOrderRecord created deterministically.
    assert record.order_id == "PAPER-000001"
    assert record.status is PaperOrderStatus.OPEN

    # Assert record fields match plan.
    assert record.symbol == symbol
    assert record.quantity == plan.quantity
    assert record.planned_entry_price == pytest.approx(entry_premium)

    # Assert PaperPosition opened.
    position = session.find_position(symbol)
    assert isinstance(position, PaperPosition)
    assert position is not None
    assert position.symbol == symbol
    assert position.quantity == plan.quantity
    assert position.average_entry_price == pytest.approx(entry_premium)

    # Assert session query helpers.
    assert session.list_orders() == (record,)
    assert session.list_open_positions() == (position,)


def test_option_buy_plan_to_paper_session_merges_two_orders_into_weighted_average_position():
    session = PaperTradingSession()

    symbol = "NIFTY26JUL24200CE"
    lots = 1

    plan_low = _approved_plan(symbol=symbol, lots=lots, entry_premium=100.0)
    plan_high = _approved_plan(symbol=symbol, lots=lots, entry_premium=120.0)

    record1 = session.submit_order(
        create_paper_order_request_from_option_buy_plan(plan_low)
    )
    record2 = session.submit_order(
        create_paper_order_request_from_option_buy_plan(plan_high)
    )

    assert record1.order_id == "PAPER-000001"
    assert record2.order_id == "PAPER-000002"

    # Both orders recorded.
    orders = session.list_orders()
    assert [o.order_id for o in orders] == ["PAPER-000001", "PAPER-000002"]
    assert len(orders) == 2

    # Position merged with weighted average entry price.
    position = session.find_position(symbol)
    assert position is not None
    assert position.quantity == plan_low.quantity + plan_high.quantity

    expected_avg = (
        plan_low.quantity * plan_low.entry_premium
        + plan_high.quantity * plan_high.entry_premium
    ) / (plan_low.quantity + plan_high.quantity)
    assert position.average_entry_price == pytest.approx(expected_avg)

    # Only one merged open position.
    assert len(session.list_open_positions()) == 1
    assert session.list_open_positions()[0].symbol == symbol


def test_workflow_smoke_test_has_no_forbidden_external_sdk_strings_in_production_files():
    production_paths = [
        Path("src/paper_trading/option_buy_plan_to_paper_order.py"),
        Path("src/paper_trading/paper_trading_session.py"),
    ]

    forbidden_tokens = [
        "fy" + "ers",
        "place" + "_order",
        "send" + "_order",
        "execute" + "_order",
    ]

    for production_path in production_paths:
        source = production_path.read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in source




    # Avoid any broker order execution API names.
    # (Split tokens to avoid self-trigger from this test's own guard strings.)
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source




