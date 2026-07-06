"""
Paper Trading Journal Store Tests

Fake/local journal persistence only. No real orders. No broker code.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_journal_store import (
    PAPER_TRADING_JOURNAL_RUN_FILENAMES,
    PaperTradingJournalRunPaths,
    build_paper_trading_journal_run_id,
    clean_paper_trading_journal_run,
    write_paper_trading_journal_run,
)
from src.paper_trading.paper_trading_session import PaperTradingSession

_OPENED_AT = datetime(2026, 7, 6, 9, 15, tzinfo=timezone.utc)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc)


def _request(**kwargs) -> PaperOrderRequest:
    defaults = dict(
        symbol="NIFTY26JUL24200CE",
        quantity=65,
        planned_entry_price=100.0,
        created_at=_OPENED_AT,
        plan_id="journal-plan-1",
    )
    defaults.update(kwargs)
    return PaperOrderRequest(**defaults)


def _session_with_open_and_closed_positions() -> PaperTradingSession:
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE"))
    session.submit_order(
        _request(
            symbol="NIFTY26JUL24300PE",
            quantity=130,
            planned_entry_price=90.0,
            plan_id="journal-plan-2",
        )
    )
    session.close_position_with_exit_record(
        "NIFTY26JUL24200CE",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.TARGET,
        exit_price=135.0,
        estimated_exit_charges=40.0,
        estimated_slippage=10.0,
    )
    return session


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_paper_trading_journal_run_id_uses_utc_timestamp():
    assert build_paper_trading_journal_run_id(_CLOSED_AT) == "20260706T093000Z"


def test_write_paper_trading_journal_run_creates_expected_files(tmp_path):
    session = _session_with_open_and_closed_positions()

    paths = write_paper_trading_journal_run(
        session,
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="demo run/1",
        generated_at=_CLOSED_AT,
    )

    assert isinstance(paths, PaperTradingJournalRunPaths)
    assert paths.output_dir.name == "demo-run-1"

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


def test_write_paper_trading_journal_run_writes_metadata_and_manifest(tmp_path):
    session = _session_with_open_and_closed_positions()

    paths = write_paper_trading_journal_run(
        session,
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="journal-001",
        generated_at=_CLOSED_AT,
    )

    metadata = _read_json(paths.metadata_json)
    manifest = _read_json(paths.manifest_json)

    assert metadata == {
        "journal_version": 1,
        "journal_source": "paper",
        "run_id": "journal-001",
        "generated_at": "2026-07-06T09:30:00+00:00",
        "paper_journal_is_local_only": True,
        "paper_pnl_is_simulation_only": True,
    }

    assert manifest["run_id"] == "journal-001"
    assert manifest["files"]["summary_json"] == str(paths.summary_json)
    assert manifest["files"]["orders_json"] == str(paths.orders_json)
    assert manifest["files"]["exit_records_json"] == str(paths.exit_records_json)


def test_write_paper_trading_journal_run_writes_session_payloads(tmp_path):
    session = _session_with_open_and_closed_positions()

    paths = write_paper_trading_journal_run(
        session,
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="journal-002",
        generated_at=_CLOSED_AT,
    )

    summary = _read_json(paths.summary_json)
    orders = _read_json(paths.orders_json)
    open_positions = _read_json(paths.open_positions_json)
    exit_records = _read_json(paths.exit_records_json)

    assert summary["run_id"] == "journal-002"
    assert summary["total_orders"] == 2
    assert summary["open_positions_count"] == 1
    assert summary["closed_trades_count"] == 1
    assert summary["total_simulated_gross_pnl"] == 2275.0
    assert summary["total_estimated_costs"] == 50.0
    assert summary["total_simulated_net_pnl"] == 2225.0

    assert len(orders) == 2
    assert orders[0]["order_id"] == "PAPER-000001"
    assert orders[1]["order_id"] == "PAPER-000002"

    assert len(open_positions) == 1
    assert open_positions[0]["symbol"] == "NIFTY26JUL24300PE"

    assert len(exit_records) == 1
    assert exit_records[0]["exit_id"] == "PAPER-EXIT-000001"
    assert exit_records[0]["symbol"] == "NIFTY26JUL24200CE"


def test_write_paper_trading_journal_run_requires_reports_directory(tmp_path):
    session = PaperTradingSession()

    with pytest.raises(ValueError, match="must be written under reports"):
        write_paper_trading_journal_run(
            session,
            tmp_path / "paper_trading" / "journal",
            run_id="bad",
            generated_at=_CLOSED_AT,
        )


def test_paper_trading_journal_store_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_journal_store.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_clean_paper_trading_journal_run_removes_only_known_generated_files(tmp_path):
    output_dir = tmp_path / "reports" / "paper_trading" / "journal"
    run_dir = output_dir / "cleanup-demo"
    run_dir.mkdir(parents=True)

    known_files = []
    for filename in PAPER_TRADING_JOURNAL_RUN_FILENAMES:
        path = run_dir / filename
        path.write_text("generated", encoding="utf-8")
        known_files.append(path)

    unknown_file = run_dir / "keep-me.txt"
    unknown_file.write_text("do not delete", encoding="utf-8")

    removed = clean_paper_trading_journal_run(output_dir, run_id="cleanup-demo")

    assert removed == tuple(known_files)

    for path in known_files:
        assert not path.exists()

    assert unknown_file.exists()
    assert unknown_file.read_text(encoding="utf-8") == "do not delete"


def test_clean_paper_trading_journal_run_returns_empty_for_missing_run(tmp_path):
    removed = clean_paper_trading_journal_run(
        tmp_path / "reports" / "paper_trading" / "journal",
        run_id="missing-run",
    )

    assert removed == ()


def test_clean_paper_trading_journal_run_requires_reports_directory(tmp_path):
    with pytest.raises(ValueError, match="must be written under reports"):
        clean_paper_trading_journal_run(
            tmp_path / "paper_trading" / "journal",
            run_id="bad",
        )


def test_clean_paper_trading_journal_run_rejects_known_path_directory(tmp_path):
    output_dir = tmp_path / "reports" / "paper_trading" / "journal"
    bad_path = output_dir / "bad-run" / "summary.json"
    bad_path.mkdir(parents=True)

    with pytest.raises(ValueError, match="not a file"):
        clean_paper_trading_journal_run(output_dir, run_id="bad-run")
