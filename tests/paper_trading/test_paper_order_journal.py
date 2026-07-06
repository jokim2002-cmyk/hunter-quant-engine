"""
Paper Order Journal Tests

Fake/local paper trading records only. No real orders. No broker code.
No FYERS. Not live market data. Not a profitability claim.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import (
    PaperOrderJournal,
    PaperOrderRecord,
    PaperOrderRequest,
    PaperOrderStatus,
)

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


# --- PaperOrderRequest validation ---

def test_request_rejects_blank_symbol():
    with pytest.raises(ValueError, match="symbol is required"):
        _request(symbol="")


def test_request_rejects_whitespace_symbol():
    with pytest.raises(ValueError, match="symbol is required"):
        _request(symbol="   ")


def test_request_rejects_zero_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        _request(quantity=0)


def test_request_rejects_negative_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        _request(quantity=-1)


def test_request_rejects_zero_entry_price():
    with pytest.raises(ValueError, match="planned_entry_price must be greater than 0"):
        _request(planned_entry_price=0.0)


def test_request_rejects_negative_entry_price():
    with pytest.raises(ValueError, match="planned_entry_price must be greater than 0"):
        _request(planned_entry_price=-5.0)


def test_request_accepts_valid_fields():
    req = _request()
    assert req.symbol == "NIFTY_24200CE"
    assert req.quantity == 65
    assert req.planned_entry_price == 120.0
    assert req.created_at == _TS


# --- PaperOrderRecord source guard ---

def test_record_rejects_non_paper_source():
    with pytest.raises(ValueError, match="source must be 'paper'"):
        PaperOrderRecord(
            order_id="PAPER-000001",
            symbol="NIFTY_24200CE",
            quantity=65,
            planned_entry_price=120.0,
            status=PaperOrderStatus.OPEN,
            created_at=_TS,
            source="live",
        )


# --- PaperOrderJournal ---

def test_journal_records_valid_request():
    journal = PaperOrderJournal()
    record = journal.record(_request())

    assert isinstance(record, PaperOrderRecord)
    assert record.symbol == "NIFTY_24200CE"
    assert record.quantity == 65
    assert record.planned_entry_price == 120.0
    assert record.status is PaperOrderStatus.OPEN
    assert record.source == "paper"
    assert record.created_at == _TS


def test_journal_assigns_first_order_id():
    journal = PaperOrderJournal()
    record = journal.record(_request())

    assert record.order_id == "PAPER-000001"


def test_journal_increments_order_id_deterministically():
    journal = PaperOrderJournal()
    r1 = journal.record(_request())
    r2 = journal.record(_request())
    r3 = journal.record(_request())

    assert r1.order_id == "PAPER-000001"
    assert r2.order_id == "PAPER-000002"
    assert r3.order_id == "PAPER-000003"


def test_journal_stores_multiple_records():
    journal = PaperOrderJournal()
    journal.record(_request(symbol="NIFTY_24200CE"))
    journal.record(_request(symbol="NIFTY_24300PE"))

    assert len(journal.all_records()) == 2


def test_journal_all_records_returns_insertion_order():
    journal = PaperOrderJournal()
    journal.record(_request(symbol="NIFTY_24200CE"))
    journal.record(_request(symbol="NIFTY_24300PE"))

    records = journal.all_records()
    assert records[0].symbol == "NIFTY_24200CE"
    assert records[1].symbol == "NIFTY_24300PE"


def test_journal_find_by_order_id_returns_matching_record():
    journal = PaperOrderJournal()
    journal.record(_request())
    r2 = journal.record(_request(symbol="NIFTY_24300PE"))

    found = journal.find_by_order_id("PAPER-000002")
    assert found is r2
    assert found.symbol == "NIFTY_24300PE"


def test_journal_find_by_order_id_returns_none_for_unknown():
    journal = PaperOrderJournal()
    journal.record(_request())

    assert journal.find_by_order_id("PAPER-999999") is None


def test_journal_all_records_empty_on_new_journal():
    journal = PaperOrderJournal()
    assert journal.all_records() == ()


def test_journal_record_stores_plan_id():
    journal = PaperOrderJournal()
    record = journal.record(_request(plan_id="plan-abc"))

    assert record.plan_id == "plan-abc"


def test_journal_record_status_is_open():
    journal = PaperOrderJournal()
    record = journal.record(_request())

    assert record.status is PaperOrderStatus.OPEN


def test_journal_record_source_is_paper():
    journal = PaperOrderJournal()
    record = journal.record(_request())

    assert record.source == "paper"


def test_paper_order_status_values_are_defined():
    assert PaperOrderStatus.OPEN.value == "open"
    assert PaperOrderStatus.CLOSED_TP.value == "closed_tp"
    assert PaperOrderStatus.CLOSED_SL.value == "closed_sl"
    assert PaperOrderStatus.CLOSED_MANUAL.value == "closed_manual"


def test_no_broker_or_fyers_in_production_module():
    # Split the forbidden word so this guard does not self-trigger on its own source.
    forbidden = "fy" + "ers"
    source = Path("src/paper_trading/paper_order_journal.py").read_text(encoding="utf-8").lower()
    assert forbidden not in source
    assert "place_order" not in source
    assert "submit_order" not in source


def test_no_real_order_placement_method_in_journal():
    source = Path("src/paper_trading/paper_order_journal.py").read_text(encoding="utf-8").lower()
    assert "place_order" not in source
    assert "submit_order" not in source
    assert "send_order" not in source
