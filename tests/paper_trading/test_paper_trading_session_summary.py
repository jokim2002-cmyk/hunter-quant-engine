from datetime import datetime, timezone
from pathlib import Path

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    PaperTradingSessionSummary,
    build_paper_trading_session_summary,
)


def _request(
    symbol: str = "NIFTY26JUL24200CE",
    quantity: int = 65,
    planned_entry_price: float = 100.0,
) -> PaperOrderRequest:
    return PaperOrderRequest(
        symbol=symbol,
        quantity=quantity,
        planned_entry_price=planned_entry_price,
        created_at=datetime(2026, 7, 6, 9, 15, tzinfo=timezone.utc),
    )


def test_empty_session_summary():
    session = PaperTradingSession()

    summary = build_paper_trading_session_summary(session)

    assert isinstance(summary, PaperTradingSessionSummary)
    assert summary.total_orders == 0
    assert summary.open_positions_count == 0
    assert summary.total_open_quantity == 0
    assert summary.symbols == ()
    assert summary.has_open_positions is False


def test_session_summary_after_one_order():
    session = PaperTradingSession()
    session.submit_order(_request())

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 1
    assert summary.open_positions_count == 1
    assert summary.total_open_quantity == 65
    assert summary.symbols == ("NIFTY26JUL24200CE",)
    assert summary.has_open_positions is True


def test_session_summary_after_multiple_symbols():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=65))
    session.submit_order(_request(symbol="NIFTY26JUL24300CE", quantity=130))

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 2
    assert summary.open_positions_count == 2
    assert summary.total_open_quantity == 195
    assert summary.symbols == ("NIFTY26JUL24200CE", "NIFTY26JUL24300CE")


def test_session_summary_after_merged_symbol_position():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=65))
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=130))

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 2
    assert summary.open_positions_count == 1
    assert summary.total_open_quantity == 195
    assert summary.symbols == ("NIFTY26JUL24200CE",)


def test_no_forbidden_external_sdk_strings_in_summary_source():
    source = Path("src/paper_trading/paper_trading_session_summary.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_session_summary_after_closed_position():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=65))
    session.close_position("NIFTY26JUL24200CE")

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 1
    assert summary.open_positions_count == 0
    assert summary.total_open_quantity == 0
    assert summary.symbols == ()
    assert summary.has_open_positions is False


def test_session_summary_after_one_of_two_positions_is_closed():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=65))
    session.submit_order(_request(symbol="NIFTY26JUL24300CE", quantity=130))
    session.close_position("NIFTY26JUL24200CE")

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 2
    assert summary.open_positions_count == 1
    assert summary.total_open_quantity == 130
    assert summary.symbols == ("NIFTY26JUL24300CE",)
    assert summary.has_open_positions is True

