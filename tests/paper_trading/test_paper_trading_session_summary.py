from datetime import datetime, timezone
from pathlib import Path

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    PaperTradingSessionSummary,
    build_paper_trading_session_summary,
)


_OPENED_AT = datetime(2026, 7, 6, 9, 15, tzinfo=timezone.utc)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc)


def _request(
    symbol: str = "NIFTY26JUL24200CE",
    quantity: int = 65,
    planned_entry_price: float = 100.0,
) -> PaperOrderRequest:
    return PaperOrderRequest(
        symbol=symbol,
        quantity=quantity,
        planned_entry_price=planned_entry_price,
        created_at=_OPENED_AT,
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
    assert summary.closed_trades_count == 0
    assert summary.has_closed_trades is False
    assert summary.exits_with_pnl_count == 0
    assert summary.total_simulated_gross_pnl == 0
    assert summary.total_estimated_costs == 0
    assert summary.total_simulated_net_pnl == 0
    assert summary.paper_pnl_is_simulation_only is True
    assert summary.estimated_costs_included_in_net_pnl is True
    assert summary.gross_pnl_excludes_costs is True


def test_session_summary_after_one_order():
    session = PaperTradingSession()
    session.submit_order(_request())

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 1
    assert summary.open_positions_count == 1
    assert summary.total_open_quantity == 65
    assert summary.symbols == ("NIFTY26JUL24200CE",)
    assert summary.has_open_positions is True
    assert summary.closed_trades_count == 0
    assert summary.total_simulated_gross_pnl == 0
    assert summary.total_simulated_net_pnl == 0


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


def test_session_summary_after_closed_position_without_exit_record():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=65))
    session.close_position("NIFTY26JUL24200CE")

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 1
    assert summary.open_positions_count == 0
    assert summary.total_open_quantity == 0
    assert summary.symbols == ()
    assert summary.has_open_positions is False
    assert summary.closed_trades_count == 0
    assert summary.has_closed_trades is False


def test_session_summary_after_one_of_two_positions_is_closed_without_exit_record():
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
    assert summary.closed_trades_count == 0


def test_session_summary_after_exit_record_with_net_pnl():
    session = PaperTradingSession()
    session.submit_order(
        _request(symbol="NIFTY26JUL24200CE", quantity=130, planned_entry_price=100.0)
    )

    session.close_position_with_exit_record(
        "NIFTY26JUL24200CE",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.TARGET,
        exit_price=135.0,
        estimated_exit_charges=40.0,
        estimated_slippage=13.0,
    )

    summary = build_paper_trading_session_summary(session)

    assert summary.total_orders == 1
    assert summary.open_positions_count == 0
    assert summary.total_open_quantity == 0
    assert summary.symbols == ()
    assert summary.closed_trades_count == 1
    assert summary.has_closed_trades is True
    assert summary.exits_with_pnl_count == 1
    assert summary.total_simulated_gross_pnl == 4550.0
    assert summary.total_estimated_costs == 53.0
    assert summary.total_simulated_net_pnl == 4497.0
    assert summary.winning_exits_count == 1
    assert summary.losing_exits_count == 0
    assert summary.flat_exits_count == 0
    assert summary.unknown_pnl_exits_count == 0
    assert summary.net_winning_exits_count == 1
    assert summary.net_losing_exits_count == 0
    assert summary.net_flat_exits_count == 0
    assert summary.unknown_net_pnl_exits_count == 0


def test_session_summary_counts_losing_flat_and_unknown_exit_records():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="WIN", quantity=65, planned_entry_price=100.0))
    session.submit_order(_request(symbol="LOSS", quantity=65, planned_entry_price=100.0))
    session.submit_order(_request(symbol="FLAT", quantity=65, planned_entry_price=100.0))
    session.submit_order(
        _request(symbol="UNKNOWN", quantity=65, planned_entry_price=100.0)
    )

    session.close_position_with_exit_record("WIN", _CLOSED_AT, exit_price=110.0)
    session.close_position_with_exit_record("LOSS", _CLOSED_AT, exit_price=90.0)
    session.close_position_with_exit_record("FLAT", _CLOSED_AT, exit_price=100.0)
    session.close_position_with_exit_record("UNKNOWN", _CLOSED_AT)

    summary = build_paper_trading_session_summary(session)

    assert summary.closed_trades_count == 4
    assert summary.exits_with_pnl_count == 3
    assert summary.total_simulated_gross_pnl == 0.0
    assert summary.total_simulated_net_pnl == 0.0
    assert summary.winning_exits_count == 1
    assert summary.losing_exits_count == 1
    assert summary.flat_exits_count == 1
    assert summary.unknown_pnl_exits_count == 1
    assert summary.net_winning_exits_count == 1
    assert summary.net_losing_exits_count == 1
    assert summary.net_flat_exits_count == 1
    assert summary.unknown_net_pnl_exits_count == 1


def test_session_summary_counts_net_loss_after_costs():
    session = PaperTradingSession()
    session.submit_order(
        _request(symbol="COSTED", quantity=65, planned_entry_price=100.0)
    )

    session.close_position_with_exit_record(
        "COSTED",
        _CLOSED_AT,
        exit_price=101.0,
        estimated_exit_charges=40.0,
        estimated_slippage=30.0,
    )

    summary = build_paper_trading_session_summary(session)

    assert summary.total_simulated_gross_pnl == 65.0
    assert summary.total_estimated_costs == 70.0
    assert summary.total_simulated_net_pnl == -5.0
    assert summary.winning_exits_count == 1
    assert summary.net_losing_exits_count == 1


def test_no_forbidden_external_sdk_strings_in_summary_source():
    source = Path("src/paper_trading/paper_trading_session_summary.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
