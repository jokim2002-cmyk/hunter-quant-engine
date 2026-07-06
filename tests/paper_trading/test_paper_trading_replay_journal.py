"""
Paper Trading Replay Journal Tests

Fake/local replay journal persistence only. No real orders. No broker code.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_replay_journal import (
    PaperTradingReplayJournalResult,
    run_paper_trading_replay_journal,
)
from src.paper_trading.paper_trading_replay_loop import PaperTradingReplayStep
from src.paper_trading.paper_trading_session import PaperTradingSession

_OPENED_AT = datetime(2026, 7, 6, 9, 15, tzinfo=timezone.utc)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc)


def _request(**kwargs) -> PaperOrderRequest:
    defaults = dict(
        symbol="NIFTY26JUL24200CE",
        quantity=65,
        planned_entry_price=100.0,
        created_at=_OPENED_AT,
        plan_id="replay-journal-plan",
    )
    defaults.update(kwargs)
    return PaperOrderRequest(**defaults)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_replay_journal_runs_replay_and_writes_journal_bundle(tmp_path):
    result = run_paper_trading_replay_journal(
        (
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=_request(),
            ),
            PaperTradingReplayStep(
                timestamp=_CLOSED_AT,
                close_symbol="NIFTY26JUL24200CE",
                exit_reason=PaperExitReason.TARGET,
                exit_price=135.0,
                estimated_exit_charges=40.0,
                estimated_slippage=10.0,
            ),
        ),
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="replay-journal-001",
        generated_at=_CLOSED_AT,
    )

    assert isinstance(result, PaperTradingReplayJournalResult)
    assert result.processed_steps == 2
    assert result.submitted_orders_count == 1
    assert result.exit_records_count == 1
    assert result.has_missing_closes is False

    paths = result.journal_paths
    for path in (
        paths.metadata_json,
        paths.summary_json,
        paths.orders_json,
        paths.open_positions_json,
        paths.exit_records_json,
        paths.manifest_json,
    ):
        assert path.exists()
        assert "reports" in [part.lower() for part in path.parts]

    summary = _read_json(paths.summary_json)
    orders = _read_json(paths.orders_json)
    exits = _read_json(paths.exit_records_json)

    assert summary["run_id"] == "replay-journal-001"
    assert summary["total_orders"] == 1
    assert summary["closed_trades_count"] == 1
    assert summary["total_simulated_gross_pnl"] == 2275.0
    assert summary["total_estimated_costs"] == 50.0
    assert summary["total_simulated_net_pnl"] == 2225.0
    assert orders[0]["plan_id"] == "replay-journal-plan"
    assert exits[0]["exit_reason"] == "target"


def test_replay_journal_uses_existing_session_when_supplied(tmp_path):
    session = PaperTradingSession()

    result = run_paper_trading_replay_journal(
        (
            PaperTradingReplayStep(
                timestamp=_OPENED_AT,
                request=_request(symbol="NIFTY26JUL24300PE"),
            ),
        ),
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="existing-session",
        generated_at=_CLOSED_AT,
        session=session,
    )

    assert result.session is session
    assert result.session.find_position("NIFTY26JUL24300PE") is not None

    summary = _read_json(result.journal_paths.summary_json)
    assert summary["run_id"] == "existing-session"
    assert summary["total_orders"] == 1
    assert summary["open_positions_count"] == 1


def test_replay_journal_preserves_missing_close_state_and_writes_empty_journal(tmp_path):
    result = run_paper_trading_replay_journal(
        (
            PaperTradingReplayStep(
                timestamp=_CLOSED_AT,
                close_symbol="NIFTY26JUL99999CE",
                exit_reason=PaperExitReason.MANUAL,
                exit_price=120.0,
            ),
        ),
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="missing-close",
        generated_at=_CLOSED_AT,
    )

    assert result.has_missing_closes is True
    assert result.replay_result.missing_close_symbols == ("NIFTY26JUL99999CE",)

    summary = _read_json(result.journal_paths.summary_json)
    orders = _read_json(result.journal_paths.orders_json)
    exits = _read_json(result.journal_paths.exit_records_json)

    assert summary["run_id"] == "missing-close"
    assert summary["total_orders"] == 0
    assert summary["closed_trades_count"] == 0
    assert orders == []
    assert exits == []


def test_paper_trading_replay_journal_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_replay_journal.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
