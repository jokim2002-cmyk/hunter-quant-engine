"""
Paper Position State Tests

Fake/local paper trading position tracking only. No real orders. No broker code.
Not live market data. Not a profitability claim.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import PaperOrderRecord, PaperOrderStatus
from src.paper_trading.paper_position_state import PaperPosition, PaperPositionState

_TS = datetime(2026, 7, 6, 9, 15)


def _record(**kwargs) -> PaperOrderRecord:
    defaults = dict(
        order_id="PAPER-000001",
        symbol="NIFTY_24200CE",
        quantity=65,
        planned_entry_price=120.0,
        status=PaperOrderStatus.OPEN,
        created_at=_TS,
        source="paper",
    )
    defaults.update(kwargs)
    return PaperOrderRecord(**defaults)


# --- PaperPosition validation ---

def test_position_rejects_blank_symbol():
    with pytest.raises(ValueError, match="symbol is required"):
        PaperPosition(symbol="", quantity=65, average_entry_price=120.0, opened_at=_TS)


def test_position_rejects_whitespace_symbol():
    with pytest.raises(ValueError, match="symbol is required"):
        PaperPosition(symbol="   ", quantity=65, average_entry_price=120.0, opened_at=_TS)


def test_position_rejects_zero_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        PaperPosition(symbol="NIFTY_24200CE", quantity=0, average_entry_price=120.0, opened_at=_TS)


def test_position_rejects_negative_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        PaperPosition(symbol="NIFTY_24200CE", quantity=-1, average_entry_price=120.0, opened_at=_TS)


def test_position_rejects_zero_price():
    with pytest.raises(ValueError, match="average_entry_price must be greater than 0"):
        PaperPosition(symbol="NIFTY_24200CE", quantity=65, average_entry_price=0.0, opened_at=_TS)


def test_position_rejects_negative_price():
    with pytest.raises(ValueError, match="average_entry_price must be greater than 0"):
        PaperPosition(symbol="NIFTY_24200CE", quantity=65, average_entry_price=-5.0, opened_at=_TS)


def test_position_rejects_non_paper_source():
    with pytest.raises(ValueError, match="source must be 'paper'"):
        PaperPosition(
            symbol="NIFTY_24200CE", quantity=65, average_entry_price=120.0,
            opened_at=_TS, source="live",
        )


def test_position_source_defaults_to_paper():
    pos = PaperPosition(symbol="NIFTY_24200CE", quantity=65, average_entry_price=120.0, opened_at=_TS)
    assert pos.source == "paper"


# --- PaperPositionState.apply_order ---

def test_apply_order_opens_position_from_record():
    state = PaperPositionState()
    pos = state.apply_order(_record())

    assert isinstance(pos, PaperPosition)
    assert pos.symbol == "NIFTY_24200CE"
    assert pos.quantity == 65
    assert pos.average_entry_price == 120.0
    assert pos.opened_at == _TS
    assert pos.source == "paper"


def test_apply_order_rejects_non_paper_source():
    state = PaperPositionState()
    with pytest.raises(ValueError, match="source must be 'paper'"):
        state.apply_order(_record(source="live"))


def test_apply_order_rejects_non_open_status():
    state = PaperPositionState()
    with pytest.raises(ValueError, match="only OPEN status records can open a position"):
        state.apply_order(_record(status=PaperOrderStatus.CLOSED_TP))


def test_apply_order_rejects_closed_sl_status():
    state = PaperPositionState()
    with pytest.raises(ValueError, match="only OPEN status records can open a position"):
        state.apply_order(_record(status=PaperOrderStatus.CLOSED_SL))


def test_apply_order_rejects_closed_manual_status():
    state = PaperPositionState()
    with pytest.raises(ValueError, match="only OPEN status records can open a position"):
        state.apply_order(_record(status=PaperOrderStatus.CLOSED_MANUAL))


# --- PaperPositionState.open_positions ---

def test_open_positions_empty_on_new_state():
    state = PaperPositionState()
    assert state.open_positions() == ()


def test_open_positions_returns_all_positions():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", symbol="NIFTY_24200CE"))
    state.apply_order(_record(order_id="PAPER-000002", symbol="NIFTY_24300PE"))

    positions = state.open_positions()
    assert len(positions) == 2


def test_open_positions_returns_insertion_order():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", symbol="NIFTY_24200CE"))
    state.apply_order(_record(order_id="PAPER-000002", symbol="NIFTY_24300PE"))

    positions = state.open_positions()
    assert positions[0].symbol == "NIFTY_24200CE"
    assert positions[1].symbol == "NIFTY_24300PE"


# --- PaperPositionState.find_by_symbol ---

def test_find_by_symbol_returns_matching_position():
    state = PaperPositionState()
    state.apply_order(_record(symbol="NIFTY_24200CE"))

    found = state.find_by_symbol("NIFTY_24200CE")
    assert found is not None
    assert found.symbol == "NIFTY_24200CE"


def test_find_by_symbol_returns_none_for_unknown():
    state = PaperPositionState()
    state.apply_order(_record(symbol="NIFTY_24200CE"))

    assert state.find_by_symbol("NIFTY_99999CE") is None


# --- Weighted average merge ---

def test_apply_order_same_symbol_merges_quantity():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", quantity=65, planned_entry_price=100.0))
    state.apply_order(_record(order_id="PAPER-000002", quantity=65, planned_entry_price=120.0))

    pos = state.find_by_symbol("NIFTY_24200CE")
    assert pos.quantity == 130


def test_apply_order_same_symbol_calculates_weighted_average_price():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", quantity=1, planned_entry_price=100.0))
    state.apply_order(_record(order_id="PAPER-000002", quantity=1, planned_entry_price=120.0))

    pos = state.find_by_symbol("NIFTY_24200CE")
    assert pos.average_entry_price == 110.0


def test_apply_order_weighted_average_unequal_quantities():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", quantity=2, planned_entry_price=100.0))
    state.apply_order(_record(order_id="PAPER-000002", quantity=1, planned_entry_price=130.0))

    pos = state.find_by_symbol("NIFTY_24200CE")
    assert pos.quantity == 3
    assert abs(pos.average_entry_price - 110.0) < 1e-9


def test_apply_order_merge_preserves_original_opened_at():
    ts1 = datetime(2026, 7, 6, 9, 15)
    ts2 = datetime(2026, 7, 6, 9, 20)
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", created_at=ts1))
    state.apply_order(_record(order_id="PAPER-000002", created_at=ts2))

    pos = state.find_by_symbol("NIFTY_24200CE")
    assert pos.opened_at == ts1


# --- total_quantity ---

def test_total_quantity_returns_zero_for_unknown_symbol():
    state = PaperPositionState()
    assert state.total_quantity("NIFTY_99999CE") == 0


def test_total_quantity_returns_quantity_for_known_symbol():
    state = PaperPositionState()
    state.apply_order(_record(quantity=65))
    assert state.total_quantity("NIFTY_24200CE") == 65


def test_total_quantity_reflects_merged_quantity():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", quantity=65))
    state.apply_order(_record(order_id="PAPER-000002", quantity=65))
    assert state.total_quantity("NIFTY_24200CE") == 130


# --- close ---

def test_close_removes_position():
    state = PaperPositionState()
    state.apply_order(_record())
    closed = state.close("NIFTY_24200CE")

    assert closed is not None
    assert closed.symbol == "NIFTY_24200CE"
    assert state.find_by_symbol("NIFTY_24200CE") is None


def test_close_returns_none_for_unknown_symbol():
    state = PaperPositionState()
    assert state.close("NIFTY_99999CE") is None


def test_close_reduces_open_positions_count():
    state = PaperPositionState()
    state.apply_order(_record(order_id="PAPER-000001", symbol="NIFTY_24200CE"))
    state.apply_order(_record(order_id="PAPER-000002", symbol="NIFTY_24300PE"))
    state.close("NIFTY_24200CE")

    positions = state.open_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "NIFTY_24300PE"


# --- broker/FYERS guard ---

def test_no_broker_or_fyers_in_production_module():
    forbidden = "fy" + "ers"
    source = Path("src/paper_trading/paper_position_state.py").read_text(encoding="utf-8").lower()
    assert forbidden not in source
    assert "place_order" not in source
    assert "submit_order" not in source
    assert "send_order" not in source
