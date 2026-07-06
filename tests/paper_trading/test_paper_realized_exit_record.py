"""
Paper Realized Exit Record Tests

Fake/local paper trading exit snapshots only. No real orders. No broker code.
Not live market data. Not a profitability claim.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_position_state import PaperPosition
from src.paper_trading.paper_realized_exit_record import (
    PaperExitReason,
    PaperRealizedExitRecord,
    create_paper_realized_exit_record,
)
from src.paper_trading.paper_trading_session import PaperTradingSession

_OPENED_AT = datetime(2026, 7, 6, 9, 15)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30)


def _position(**kwargs) -> PaperPosition:
    defaults = dict(
        symbol="NIFTY_24200CE",
        quantity=65,
        average_entry_price=120.0,
        opened_at=_OPENED_AT,
    )
    defaults.update(kwargs)
    return PaperPosition(**defaults)


def _request(**kwargs) -> PaperOrderRequest:
    defaults = dict(
        symbol="NIFTY_24200CE",
        quantity=65,
        planned_entry_price=120.0,
        created_at=_OPENED_AT,
    )
    defaults.update(kwargs)
    return PaperOrderRequest(**defaults)


def test_realized_exit_record_accepts_valid_values():
    record = PaperRealizedExitRecord(
        exit_id="PAPER-EXIT-000001",
        symbol="NIFTY_24200CE",
        quantity=65,
        average_entry_price=120.0,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.MANUAL,
    )

    assert record.exit_id == "PAPER-EXIT-000001"
    assert record.symbol == "NIFTY_24200CE"
    assert record.quantity == 65
    assert record.average_entry_price == 120.0
    assert record.opened_at == _OPENED_AT
    assert record.closed_at == _CLOSED_AT
    assert record.exit_reason is PaperExitReason.MANUAL
    assert record.source == "paper"


def test_realized_exit_record_rejects_blank_exit_id():
    with pytest.raises(ValueError, match="exit_id is required"):
        PaperRealizedExitRecord(
            exit_id="",
            symbol="NIFTY_24200CE",
            quantity=65,
            average_entry_price=120.0,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            exit_reason=PaperExitReason.MANUAL,
        )


def test_realized_exit_record_rejects_blank_symbol():
    with pytest.raises(ValueError, match="symbol is required"):
        PaperRealizedExitRecord(
            exit_id="PAPER-EXIT-000001",
            symbol="",
            quantity=65,
            average_entry_price=120.0,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            exit_reason=PaperExitReason.MANUAL,
        )


def test_realized_exit_record_rejects_zero_quantity():
    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        PaperRealizedExitRecord(
            exit_id="PAPER-EXIT-000001",
            symbol="NIFTY_24200CE",
            quantity=0,
            average_entry_price=120.0,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            exit_reason=PaperExitReason.MANUAL,
        )


def test_realized_exit_record_rejects_zero_entry_price():
    with pytest.raises(ValueError, match="average_entry_price must be greater than 0"):
        PaperRealizedExitRecord(
            exit_id="PAPER-EXIT-000001",
            symbol="NIFTY_24200CE",
            quantity=65,
            average_entry_price=0.0,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            exit_reason=PaperExitReason.MANUAL,
        )


def test_realized_exit_record_rejects_closed_at_before_opened_at():
    with pytest.raises(ValueError, match="closed_at must be after or equal to opened_at"):
        PaperRealizedExitRecord(
            exit_id="PAPER-EXIT-000001",
            symbol="NIFTY_24200CE",
            quantity=65,
            average_entry_price=120.0,
            opened_at=_CLOSED_AT,
            closed_at=_OPENED_AT,
            exit_reason=PaperExitReason.MANUAL,
        )


def test_realized_exit_record_rejects_non_enum_exit_reason():
    with pytest.raises(ValueError, match="exit_reason must be PaperExitReason"):
        PaperRealizedExitRecord(
            exit_id="PAPER-EXIT-000001",
            symbol="NIFTY_24200CE",
            quantity=65,
            average_entry_price=120.0,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            exit_reason="manual",
        )


def test_realized_exit_record_rejects_non_paper_source():
    with pytest.raises(ValueError, match="source must be 'paper'"):
        PaperRealizedExitRecord(
            exit_id="PAPER-EXIT-000001",
            symbol="NIFTY_24200CE",
            quantity=65,
            average_entry_price=120.0,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            exit_reason=PaperExitReason.MANUAL,
            source="live",
        )


def test_create_realized_exit_record_from_position():
    record = create_paper_realized_exit_record(
        position=_position(),
        exit_id="PAPER-EXIT-000001",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.TARGET,
    )

    assert record.exit_id == "PAPER-EXIT-000001"
    assert record.symbol == "NIFTY_24200CE"
    assert record.quantity == 65
    assert record.average_entry_price == 120.0
    assert record.opened_at == _OPENED_AT
    assert record.closed_at == _CLOSED_AT
    assert record.exit_reason is PaperExitReason.TARGET
    assert record.source == "paper"


def test_create_realized_exit_record_defaults_to_manual_reason():
    record = create_paper_realized_exit_record(
        position=_position(),
        exit_id="PAPER-EXIT-000001",
        closed_at=_CLOSED_AT,
    )

    assert record.exit_reason is PaperExitReason.MANUAL


def test_session_close_position_with_exit_record_closes_position_and_records_exit():
    session = PaperTradingSession()
    session.submit_order(_request())

    exit_record = session.close_position_with_exit_record(
        "NIFTY_24200CE",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.MANUAL,
    )

    assert exit_record is not None
    assert exit_record.exit_id == "PAPER-EXIT-000001"
    assert exit_record.symbol == "NIFTY_24200CE"
    assert exit_record.quantity == 65
    assert exit_record.average_entry_price == 120.0
    assert exit_record.opened_at == _OPENED_AT
    assert exit_record.closed_at == _CLOSED_AT
    assert exit_record.exit_reason is PaperExitReason.MANUAL

    assert session.find_position("NIFTY_24200CE") is None
    assert session.total_open_quantity("NIFTY_24200CE") == 0
    assert session.list_exit_records() == (exit_record,)
    assert session.find_exit_record("PAPER-EXIT-000001") is exit_record


def test_session_close_position_with_exit_record_returns_none_for_unknown_symbol():
    session = PaperTradingSession()
    session.submit_order(_request())

    exit_record = session.close_position_with_exit_record(
        "NIFTY_99999CE",
        closed_at=_CLOSED_AT,
    )

    assert exit_record is None
    assert session.find_position("NIFTY_24200CE") is not None
    assert session.list_exit_records() == ()


def test_session_exit_record_ids_are_deterministic():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY_24200CE"))
    session.submit_order(_request(symbol="NIFTY_24300PE"))

    first = session.close_position_with_exit_record("NIFTY_24200CE", _CLOSED_AT)
    second = session.close_position_with_exit_record("NIFTY_24300PE", _CLOSED_AT)

    assert first is not None
    assert second is not None
    assert first.exit_id == "PAPER-EXIT-000001"
    assert second.exit_id == "PAPER-EXIT-000002"
    assert session.list_exit_records() == (first, second)


def test_session_find_exit_record_returns_none_for_unknown_id():
    session = PaperTradingSession()
    session.submit_order(_request())
    session.close_position_with_exit_record("NIFTY_24200CE", _CLOSED_AT)

    assert session.find_exit_record("PAPER-EXIT-999999") is None


def test_realized_exit_record_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_realized_exit_record.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_session_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_session.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
