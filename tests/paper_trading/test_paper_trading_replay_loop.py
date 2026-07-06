"""
Paper Trading Replay Loop Tests

Fake/local replay only. No real orders. No broker code.
Not live market data. Not a profitability claim.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_replay_loop import (
    PaperTradingReplayResult,
    PaperTradingReplayStep,
    run_paper_trading_replay_loop,
)
from src.paper_trading.paper_trading_session import PaperTradingSession

_OPENED_AT = datetime(2026, 7, 6, 9, 15)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30)


def _request(**kwargs) -> PaperOrderRequest:
    defaults = dict(
        symbol="NIFTY26JUL24200CE",
        quantity=65,
        planned_entry_price=100.0,
        created_at=_OPENED_AT,
    )
    defaults.update(kwargs)
    return PaperOrderRequest(**defaults)


def test_replay_loop_submits_order_and_creates_exit_record_with_net_pnl():
    result = run_paper_trading_replay_loop(
        (
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=_request(plan_id="replay-plan-1"),
            ),
            PaperTradingReplayStep(
                timestamp=_CLOSED_AT,
                close_symbol="NIFTY26JUL24200CE",
                exit_reason=PaperExitReason.TARGET,
                exit_price=135.0,
                estimated_exit_charges=40.0,
                estimated_slippage=10.0,
            ),
        )
    )

    assert isinstance(result, PaperTradingReplayResult)
    assert result.processed_steps == 2
    assert result.submitted_orders_count == 1
    assert result.exit_records_count == 1
    assert result.has_missing_closes is False
    assert result.missing_close_symbols == ()
    assert result.session.list_orders() == result.submitted_orders
    assert result.session.list_exit_records() == result.exit_records

    order = result.submitted_orders[0]
    assert order.order_id == "PAPER-000001"
    assert order.plan_id == "replay-plan-1"

    exit_record = result.exit_records[0]
    assert exit_record.exit_id == "PAPER-EXIT-000001"
    assert exit_record.symbol == "NIFTY26JUL24200CE"
    assert exit_record.exit_reason is PaperExitReason.TARGET
    assert exit_record.simulated_gross_pnl == 2275.0
    assert exit_record.total_estimated_costs == 50.0
    assert exit_record.simulated_net_pnl == 2225.0


def test_replay_loop_merges_multiple_open_steps_for_same_symbol():
    result = run_paper_trading_replay_loop(
        (
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=_request(quantity=1, planned_entry_price=100.0),
            ),
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=_request(quantity=3, planned_entry_price=120.0),
            ),
        )
    )

    position = result.session.find_position("NIFTY26JUL24200CE")

    assert position is not None
    assert position.quantity == 4
    assert position.average_entry_price == 115.0
    assert result.submitted_orders_count == 2
    assert result.exit_records_count == 0


def test_replay_loop_records_missing_close_without_failing_replay():
    result = run_paper_trading_replay_loop(
        (
            PaperTradingReplayStep(
                timestamp=_CLOSED_AT,
                close_symbol="NIFTY26JUL99999CE",
                exit_reason=PaperExitReason.MANUAL,
                exit_price=120.0,
            ),
        )
    )

    assert result.processed_steps == 1
    assert result.submitted_orders == ()
    assert result.exit_records == ()
    assert result.missing_close_symbols == ("NIFTY26JUL99999CE",)
    assert result.has_missing_closes is True


def test_replay_loop_can_use_existing_session():
    session = PaperTradingSession()

    result = run_paper_trading_replay_loop(
        (
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=_request(symbol="NIFTY26JUL24300PE"),
            ),
        ),
        session=session,
    )

    assert result.session is session
    assert session.find_position("NIFTY26JUL24300PE") is not None


def test_replay_step_validation_rejects_invalid_local_replay_steps():
    with pytest.raises(ValueError, match="requires a request or close_symbol"):
        PaperTradingReplayStep(timestamp=_OPENED_AT)

    with pytest.raises(ValueError, match="exit_price must be greater than 0"):
        PaperTradingReplayStep(
            timestamp=_CLOSED_AT,
            close_symbol="NIFTY26JUL24200CE",
            exit_price=0.0,
        )

    with pytest.raises(ValueError, match="exit details require close_symbol"):
        PaperTradingReplayStep(timestamp=_CLOSED_AT, exit_price=120.0)


def test_replay_loop_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_replay_loop.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
