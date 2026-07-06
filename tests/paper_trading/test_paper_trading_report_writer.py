"""
Paper Trading Report Writer Tests

Fake/local paper trading reports only. No real orders. No broker code.
Not live market data. Not a profitability claim.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_report_writer import (
    PaperTradingReportPaths,
    paper_exit_record_to_dict,
    paper_order_record_to_dict,
    paper_position_to_dict,
    write_paper_trading_report,
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


def _session_with_open_and_closed_positions() -> PaperTradingSession:
    session = PaperTradingSession()
    session.submit_order(_request(symbol="NIFTY26JUL24200CE", quantity=65))
    session.submit_order(
        _request(symbol="NIFTY26JUL24300CE", quantity=130, planned_entry_price=120.0)
    )
    session.close_position_with_exit_record(
        "NIFTY26JUL24200CE",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.TARGET,
        exit_price=135.0,
    )
    return session


def test_paper_order_record_to_dict():
    session = PaperTradingSession()
    record = session.submit_order(_request(plan_id="demo-plan"))

    payload = paper_order_record_to_dict(record)

    assert payload == {
        "order_id": "PAPER-000001",
        "symbol": "NIFTY26JUL24200CE",
        "quantity": 65,
        "planned_entry_price": 100.0,
        "status": "open",
        "created_at": _OPENED_AT.isoformat(),
        "source": "paper",
        "plan_id": "demo-plan",
    }


def test_paper_position_to_dict():
    session = PaperTradingSession()
    session.submit_order(_request())

    position = session.find_position("NIFTY26JUL24200CE")
    assert position is not None

    payload = paper_position_to_dict(position)

    assert payload == {
        "symbol": "NIFTY26JUL24200CE",
        "quantity": 65,
        "average_entry_price": 100.0,
        "opened_at": _OPENED_AT.isoformat(),
        "source": "paper",
    }


def test_paper_exit_record_to_dict():
    session = PaperTradingSession()
    session.submit_order(_request())
    exit_record = session.close_position_with_exit_record(
        "NIFTY26JUL24200CE",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.TARGET,
        exit_price=135.0,
    )

    assert exit_record is not None

    payload = paper_exit_record_to_dict(exit_record)

    assert payload == {
        "exit_id": "PAPER-EXIT-000001",
        "symbol": "NIFTY26JUL24200CE",
        "quantity": 65,
        "average_entry_price": 100.0,
        "opened_at": _OPENED_AT.isoformat(),
        "closed_at": _CLOSED_AT.isoformat(),
        "exit_reason": "target",
        "exit_price": 135.0,
        "has_exit_price": True,
        "simulated_points": 35.0,
        "simulated_gross_pnl": 2275.0,
        "source": "paper",
    }


def test_write_paper_trading_report_creates_expected_files(tmp_path):
    session = _session_with_open_and_closed_positions()
    output_dir = tmp_path / "reports" / "paper_trading"

    paths = write_paper_trading_report(session, output_dir)

    assert isinstance(paths, PaperTradingReportPaths)
    assert paths.output_dir == output_dir

    expected_paths = [
        paths.summary_json,
        paths.summary_csv,
        paths.orders_json,
        paths.orders_csv,
        paths.open_positions_json,
        paths.open_positions_csv,
        paths.exit_records_json,
        paths.exit_records_csv,
        paths.report_text,
    ]

    for path in expected_paths:
        assert path.exists()
        assert "reports" in [part.lower() for part in path.parts]


def test_write_paper_trading_report_writes_summary_json(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(session, tmp_path / "reports" / "paper")

    payload = json.loads(paths.summary_json.read_text(encoding="utf-8"))

    assert payload == {
        "total_orders": 2,
        "open_positions_count": 1,
        "total_open_quantity": 130,
        "symbols": ["NIFTY26JUL24300CE"],
        "has_open_positions": True,
    }


def test_write_paper_trading_report_writes_orders_json(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(session, tmp_path / "reports" / "paper")

    payload = json.loads(paths.orders_json.read_text(encoding="utf-8"))

    assert len(payload) == 2
    assert payload[0]["order_id"] == "PAPER-000001"
    assert payload[0]["symbol"] == "NIFTY26JUL24200CE"
    assert payload[1]["order_id"] == "PAPER-000002"
    assert payload[1]["symbol"] == "NIFTY26JUL24300CE"


def test_write_paper_trading_report_writes_open_positions_csv(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(session, tmp_path / "reports" / "paper")

    with paths.open_positions_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "symbol": "NIFTY26JUL24300CE",
            "quantity": "130",
            "average_entry_price": "120.0",
            "opened_at": _OPENED_AT.isoformat(),
            "source": "paper",
        }
    ]


def test_write_paper_trading_report_writes_exit_records_csv(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(session, tmp_path / "reports" / "paper")

    with paths.exit_records_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "exit_id": "PAPER-EXIT-000001",
            "symbol": "NIFTY26JUL24200CE",
            "quantity": "65",
            "average_entry_price": "100.0",
            "opened_at": _OPENED_AT.isoformat(),
            "closed_at": _CLOSED_AT.isoformat(),
            "exit_reason": "target",
            "exit_price": "135.0",
            "has_exit_price": "True",
            "simulated_points": "35.0",
            "simulated_gross_pnl": "2275.0",
            "source": "paper",
        }
    ]


def test_write_paper_trading_report_text_contains_safety_lines(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(session, tmp_path / "reports" / "paper")

    text = paths.report_text.read_text(encoding="utf-8").lower()

    assert "paper trading session summary" in text
    assert "paper trading report files" in text
    assert "orders count: 2" in text
    assert "open positions count: 1" in text
    assert "exit records count: 1" in text
    assert "paper pnl is simulation only" in text
    assert "charges and slippage are not included" in text
    assert "local report/export only" in text
    assert "no broker/fyers" in text
    assert "no live/real market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text


def test_write_paper_trading_report_rejects_output_outside_reports(tmp_path):
    session = _session_with_open_and_closed_positions()

    with pytest.raises(ValueError, match="reports/"):
        write_paper_trading_report(session, tmp_path / "paper_trading")


def test_write_empty_paper_trading_report(tmp_path):
    session = PaperTradingSession()
    paths = write_paper_trading_report(session, tmp_path / "reports" / "empty")

    summary_payload = json.loads(paths.summary_json.read_text(encoding="utf-8"))
    orders_payload = json.loads(paths.orders_json.read_text(encoding="utf-8"))
    positions_payload = json.loads(paths.open_positions_json.read_text(encoding="utf-8"))
    exits_payload = json.loads(paths.exit_records_json.read_text(encoding="utf-8"))

    assert summary_payload["total_orders"] == 0
    assert orders_payload == []
    assert positions_payload == []
    assert exits_payload == []


def test_report_writer_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_report_writer.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
