"""
Paper Trading Session Tests

Fake/local paper trading coordinator only. No real orders. No broker code.
No FYERS. Not live market data. Not a profitability claim.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import (
    PaperOrderJournal,
    PaperOrderRequest,
    PaperOrderStatus,
)
from src.paper_trading.paper_position_state import PaperPositionState
from src.paper_trading.paper_trading_session import PaperTradingSession

_TS = datetime(2026, 7, 6, 9, 15)


def _request(**kwargs) -> PaperOrderRequest:
    defaults = dict(
        symbol="NIFTY_24200CE",
        quantity=65,
        planned_entry_price=120.0,
        created_at=_TS,
    )
    defaults.update(kwargs)
    return PaperOrderRequest(**defaults)


def test_submit_valid_request_creates_paper_order_record():
    session = PaperTradingSession()

    record = session.submit_order(_request())

    assert record.order_id == "PAPER-000001"
    assert record.symbol == "NIFTY_24200CE"
    assert record.quantity == 65
    assert record.planned_entry_price == 120.0
    assert record.status is PaperOrderStatus.OPEN
    assert record.source == "paper"


def test_submit_valid_request_opens_paper_position():
    session = PaperTradingSession()

    session.submit_order(_request())

    position = session.find_position("NIFTY_24200CE")
    assert position is not None
    assert position.symbol == "NIFTY_24200CE"
    assert position.quantity == 65
    assert position.average_entry_price == 120.0


def test_order_id_is_deterministic_through_journal():
    session = PaperTradingSession()

    first = session.submit_order(_request())
    second = session.submit_order(_request(symbol="NIFTY_24300PE"))

    assert first.order_id == "PAPER-000001"
    assert second.order_id == "PAPER-000002"


def test_multiple_submitted_orders_are_stored():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY_24200CE"))
    session.submit_order(_request(symbol="NIFTY_24300PE"))

    assert len(session.list_orders()) == 2


def test_multiple_orders_for_same_symbol_merge_into_one_position_with_weighted_average():
    session = PaperTradingSession()
    session.submit_order(_request(quantity=1, planned_entry_price=100.0))
    session.submit_order(_request(quantity=3, planned_entry_price=120.0))

    position = session.find_position("NIFTY_24200CE")
    assert position is not None
    assert position.quantity == 4
    assert position.average_entry_price == 115.0


def test_list_orders_returns_insertion_order():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY_24200CE"))
    session.submit_order(_request(symbol="NIFTY_24300PE"))

    orders = session.list_orders()
    assert orders[0].symbol == "NIFTY_24200CE"
    assert orders[1].symbol == "NIFTY_24300PE"


def test_list_open_positions_returns_expected_positions():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY_24200CE"))
    session.submit_order(_request(symbol="NIFTY_24300PE"))

    positions = session.list_open_positions()
    assert len(positions) == 2
    assert positions[0].symbol == "NIFTY_24200CE"
    assert positions[1].symbol == "NIFTY_24300PE"


def test_find_order_returns_matching_order():
    session = PaperTradingSession()
    session.submit_order(_request())
    second = session.submit_order(_request(symbol="NIFTY_24300PE"))

    found = session.find_order(second.order_id)
    assert found is second
    assert found.symbol == "NIFTY_24300PE"


def test_find_order_unknown_returns_none():
    session = PaperTradingSession()
    session.submit_order(_request())

    assert session.find_order("PAPER-999999") is None


def test_find_position_returns_matching_position():
    session = PaperTradingSession()
    session.submit_order(_request())

    found = session.find_position("NIFTY_24200CE")
    assert found is not None
    assert found.symbol == "NIFTY_24200CE"


def test_find_position_unknown_returns_none():
    session = PaperTradingSession()
    session.submit_order(_request())

    assert session.find_position("NIFTY_99999CE") is None


def test_total_open_quantity_returns_expected_value():
    session = PaperTradingSession()
    session.submit_order(_request(quantity=10))
    session.submit_order(_request(quantity=5))

    assert session.total_open_quantity("NIFTY_24200CE") == 15


def test_blank_symbol_request_raises_value_error():
    session = PaperTradingSession()

    with pytest.raises(ValueError, match="symbol is required"):
        session.submit_order(_request(symbol=""))


def test_zero_quantity_request_raises_value_error():
    session = PaperTradingSession()

    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        session.submit_order(_request(quantity=0))


def test_negative_quantity_request_raises_value_error():
    session = PaperTradingSession()

    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        session.submit_order(_request(quantity=-1))


def test_zero_planned_entry_price_request_raises_value_error():
    session = PaperTradingSession()

    with pytest.raises(ValueError, match="planned_entry_price must be greater than 0"):
        session.submit_order(_request(planned_entry_price=0.0))


def test_negative_planned_entry_price_request_raises_value_error():
    session = PaperTradingSession()

    with pytest.raises(ValueError, match="planned_entry_price must be greater than 0"):
        session.submit_order(_request(planned_entry_price=-5.0))


def test_non_buy_request_is_rejected_if_side_exists():
    class FakeRequest:
        symbol = "NIFTY_24200CE"
        quantity = 1
        planned_entry_price = 120.0
        created_at = _TS
        side = "sell"

    session = PaperTradingSession()

    with pytest.raises(ValueError, match="only BUY paper order requests are accepted"):
        session.submit_order(FakeRequest())


def test_session_exposes_fake_local_paper_behavior_clearly():
    source = Path("src/paper_trading/paper_trading_session.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "fake/local" in source
    assert "no broker code" in source
    assert "no real orders" in source
    assert "not a profitability claim" in source


def test_no_real_order_placement_method_exists():
    source = Path("src/paper_trading/paper_trading_session.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "place_order" not in source
    assert "send_order" not in source
    assert "execute_order" not in source


def test_no_broker_or_fyers_string_appears_in_new_production_file():
    source = Path("src/paper_trading/paper_trading_session.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "fyers" not in source
    assert "broker sdk" not in source


def test_session_defaults_to_local_journal_and_position_state():
    session = PaperTradingSession()

    assert isinstance(session._journal, PaperOrderJournal)
    assert isinstance(session._position_state, PaperPositionState)
