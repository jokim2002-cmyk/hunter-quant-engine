"""
Paper Trading Report Writer Tests

Fake/local paper trading reports only. No real orders. No broker code.
Not live market data. Not a profitability claim.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_report_writer import (
    PAPER_TRADING_REPORT_SOURCE,
    PAPER_TRADING_REPORT_VERSION,
    PaperTradingReportMetadata,
    PaperTradingReportPaths,
    PaperTradingReportSummary,
    build_paper_trading_report_metadata,
    build_paper_trading_report_summary,
    paper_exit_record_to_dict,
    paper_order_record_to_dict,
    paper_position_to_dict,
    paper_trading_report_metadata_to_dict,
    paper_trading_report_summary_to_csv_row,
    paper_trading_report_summary_to_dict,
    write_paper_trading_report,
)
from src.paper_trading.paper_trading_session import PaperTradingSession

_OPENED_AT = datetime(2026, 7, 6, 9, 15)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30)
_GENERATED_AT = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
_GENERATED_AT_ISO = "2026-07-06T10:00:00+00:00"


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
        estimated_exit_charges=40.0,
        estimated_slippage=10.0,
    )
    return session


def test_build_paper_trading_report_metadata_with_fixed_time():
    metadata = build_paper_trading_report_metadata(_GENERATED_AT)

    assert isinstance(metadata, PaperTradingReportMetadata)
    assert metadata.report_version == PAPER_TRADING_REPORT_VERSION
    assert metadata.report_source == PAPER_TRADING_REPORT_SOURCE
    assert metadata.generated_at == _GENERATED_AT_ISO
    assert metadata.paper_pnl_is_simulation_only is True


def test_build_paper_trading_report_metadata_adds_timezone_to_naive_time():
    metadata = build_paper_trading_report_metadata(datetime(2026, 7, 6, 10, 0))

    assert metadata.generated_at == _GENERATED_AT_ISO


def test_paper_trading_report_metadata_to_dict():
    metadata = build_paper_trading_report_metadata(_GENERATED_AT)

    payload = paper_trading_report_metadata_to_dict(metadata)

    assert payload == {
        "report_version": 1,
        "report_source": "paper",
        "generated_at": _GENERATED_AT_ISO,
        "paper_pnl_is_simulation_only": True,
    }


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
        estimated_exit_charges=40.0,
        estimated_slippage=10.0,
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
        "estimated_exit_charges": 40.0,
        "estimated_slippage": 10.0,
        "total_estimated_costs": 50.0,
        "simulated_net_pnl": 2225.0,
        "source": "paper",
    }


def test_build_paper_trading_report_summary_with_closed_trade():
    summary = build_paper_trading_report_summary(
        _session_with_open_and_closed_positions()
    )

    assert isinstance(summary, PaperTradingReportSummary)
    assert summary.total_orders == 2
    assert summary.open_positions_count == 1
    assert summary.total_open_quantity == 130
    assert summary.symbols == ("NIFTY26JUL24300CE",)
    assert summary.has_open_positions is True
    assert summary.closed_trades_count == 1
    assert summary.has_closed_trades is True
    assert summary.exits_with_pnl_count == 1
    assert summary.total_simulated_gross_pnl == 2275.0
    assert summary.total_estimated_costs == 50.0
    assert summary.total_simulated_net_pnl == 2225.0
    assert summary.winning_exits_count == 1
    assert summary.losing_exits_count == 0
    assert summary.flat_exits_count == 0
    assert summary.unknown_pnl_exits_count == 0
    assert summary.net_winning_exits_count == 1
    assert summary.net_losing_exits_count == 0
    assert summary.net_flat_exits_count == 0
    assert summary.unknown_net_pnl_exits_count == 0
    assert summary.paper_pnl_is_simulation_only is True
    assert summary.estimated_costs_included_in_net_pnl is True
    assert summary.gross_pnl_excludes_costs is True


def test_build_paper_trading_report_summary_counts_losing_flat_and_unknown_exits():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="WIN", planned_entry_price=100.0))
    session.submit_order(_request(symbol="LOSS", planned_entry_price=100.0))
    session.submit_order(_request(symbol="FLAT", planned_entry_price=100.0))
    session.submit_order(_request(symbol="UNKNOWN", planned_entry_price=100.0))

    session.close_position_with_exit_record("WIN", _CLOSED_AT, exit_price=110.0)
    session.close_position_with_exit_record("LOSS", _CLOSED_AT, exit_price=90.0)
    session.close_position_with_exit_record("FLAT", _CLOSED_AT, exit_price=100.0)
    session.close_position_with_exit_record("UNKNOWN", _CLOSED_AT)

    summary = build_paper_trading_report_summary(session)

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


def test_build_paper_trading_report_summary_counts_net_loss_after_costs():
    session = PaperTradingSession()
    session.submit_order(_request(symbol="COSTED", planned_entry_price=100.0))

    session.close_position_with_exit_record(
        "COSTED",
        _CLOSED_AT,
        exit_price=101.0,
        estimated_exit_charges=40.0,
        estimated_slippage=30.0,
    )

    summary = build_paper_trading_report_summary(session)

    assert summary.total_simulated_gross_pnl == 65.0
    assert summary.total_estimated_costs == 70.0
    assert summary.total_simulated_net_pnl == -5.0
    assert summary.winning_exits_count == 1
    assert summary.net_losing_exits_count == 1


def test_paper_trading_report_summary_to_dict():
    summary = build_paper_trading_report_summary(
        _session_with_open_and_closed_positions()
    )

    payload = paper_trading_report_summary_to_dict(summary)

    assert payload == {
        "total_orders": 2,
        "open_positions_count": 1,
        "total_open_quantity": 130,
        "symbols": ["NIFTY26JUL24300CE"],
        "has_open_positions": True,
        "closed_trades_count": 1,
        "has_closed_trades": True,
        "exits_with_pnl_count": 1,
        "total_simulated_gross_pnl": 2275.0,
        "total_estimated_costs": 50.0,
        "total_simulated_net_pnl": 2225.0,
        "winning_exits_count": 1,
        "losing_exits_count": 0,
        "flat_exits_count": 0,
        "unknown_pnl_exits_count": 0,
        "net_winning_exits_count": 1,
        "net_losing_exits_count": 0,
        "net_flat_exits_count": 0,
        "unknown_net_pnl_exits_count": 0,
        "paper_pnl_is_simulation_only": True,
        "estimated_costs_included_in_net_pnl": True,
        "gross_pnl_excludes_costs": True,
    }


def test_paper_trading_report_summary_to_csv_row():
    summary = build_paper_trading_report_summary(
        _session_with_open_and_closed_positions()
    )

    payload = paper_trading_report_summary_to_csv_row(summary)

    assert payload["symbols"] == "NIFTY26JUL24300CE"
    assert payload["closed_trades_count"] == 1
    assert payload["total_simulated_gross_pnl"] == 2275.0
    assert payload["total_estimated_costs"] == 50.0
    assert payload["total_simulated_net_pnl"] == 2225.0


def test_write_paper_trading_report_creates_expected_files(tmp_path):
    session = _session_with_open_and_closed_positions()
    output_dir = tmp_path / "reports" / "paper_trading"

    paths = write_paper_trading_report(session, output_dir, generated_at=_GENERATED_AT)

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
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "paper",
        generated_at=_GENERATED_AT,
    )

    payload = json.loads(paths.summary_json.read_text(encoding="utf-8"))

    assert payload == {
        "report_version": 1,
        "report_source": "paper",
        "generated_at": _GENERATED_AT_ISO,
        "total_orders": 2,
        "open_positions_count": 1,
        "total_open_quantity": 130,
        "symbols": ["NIFTY26JUL24300CE"],
        "has_open_positions": True,
        "closed_trades_count": 1,
        "has_closed_trades": True,
        "exits_with_pnl_count": 1,
        "total_simulated_gross_pnl": 2275.0,
        "total_estimated_costs": 50.0,
        "total_simulated_net_pnl": 2225.0,
        "winning_exits_count": 1,
        "losing_exits_count": 0,
        "flat_exits_count": 0,
        "unknown_pnl_exits_count": 0,
        "net_winning_exits_count": 1,
        "net_losing_exits_count": 0,
        "net_flat_exits_count": 0,
        "unknown_net_pnl_exits_count": 0,
        "paper_pnl_is_simulation_only": True,
        "estimated_costs_included_in_net_pnl": True,
        "gross_pnl_excludes_costs": True,
    }


def test_write_paper_trading_report_writes_summary_csv(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "paper",
        generated_at=_GENERATED_AT,
    )

    with paths.summary_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "report_version": "1",
            "report_source": "paper",
            "generated_at": _GENERATED_AT_ISO,
            "paper_pnl_is_simulation_only": "True",
            "total_orders": "2",
            "open_positions_count": "1",
            "total_open_quantity": "130",
            "symbols": "NIFTY26JUL24300CE",
            "has_open_positions": "True",
            "closed_trades_count": "1",
            "has_closed_trades": "True",
            "exits_with_pnl_count": "1",
            "total_simulated_gross_pnl": "2275.0",
            "total_estimated_costs": "50.0",
            "total_simulated_net_pnl": "2225.0",
            "winning_exits_count": "1",
            "losing_exits_count": "0",
            "flat_exits_count": "0",
            "unknown_pnl_exits_count": "0",
            "net_winning_exits_count": "1",
            "net_losing_exits_count": "0",
            "net_flat_exits_count": "0",
            "unknown_net_pnl_exits_count": "0",
            "estimated_costs_included_in_net_pnl": "True",
            "gross_pnl_excludes_costs": "True",
        }
    ]


def test_write_paper_trading_report_writes_orders_json(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "paper",
        generated_at=_GENERATED_AT,
    )

    payload = json.loads(paths.orders_json.read_text(encoding="utf-8"))

    assert len(payload) == 2
    assert payload[0]["order_id"] == "PAPER-000001"
    assert payload[0]["symbol"] == "NIFTY26JUL24200CE"
    assert payload[1]["order_id"] == "PAPER-000002"
    assert payload[1]["symbol"] == "NIFTY26JUL24300CE"


def test_write_paper_trading_report_writes_open_positions_csv(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "paper",
        generated_at=_GENERATED_AT,
    )

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
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "paper",
        generated_at=_GENERATED_AT,
    )

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
            "estimated_exit_charges": "40.0",
            "estimated_slippage": "10.0",
            "total_estimated_costs": "50.0",
            "simulated_net_pnl": "2225.0",
            "source": "paper",
        }
    ]


def test_write_paper_trading_report_text_contains_safety_lines(tmp_path):
    session = _session_with_open_and_closed_positions()
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "paper",
        generated_at=_GENERATED_AT,
    )

    text = paths.report_text.read_text(encoding="utf-8").lower()

    assert "local paper trading report" in text
    assert "==========================" in text
    assert "report metadata" in text
    assert "---------------" in text
    assert "report version: 1" in text
    assert "report source: paper" in text
    assert f"generated at: {_GENERATED_AT_ISO.lower()}" in text
    assert "paper pnl is simulation only: true" in text
    assert "paper trading session summary" in text
    assert "-----------------------------" in text
    assert "paper trading report files" in text
    assert "orders count: 2" in text
    assert "open positions count: 1" in text
    assert "exit records count: 1" in text
    assert "paper trading p&l summary" in text
    assert "-------------------------" in text
    assert "closed trades count: 1" in text
    assert "exits with pnl count: 1" in text
    assert "total simulated gross pnl: 2275.0" in text
    assert "total estimated costs: 50.0" in text
    assert "total simulated net pnl: 2225.0" in text
    assert "winning exits count: 1" in text
    assert "losing exits count: 0" in text
    assert "flat exits count: 0" in text
    assert "unknown pnl exits count: 0" in text
    assert "net winning exits count: 1" in text
    assert "net losing exits count: 0" in text
    assert "net flat exits count: 0" in text
    assert "unknown net pnl exits count: 0" in text
    assert "paper pnl is simulation only" in text
    assert "estimated costs are included in net pnl only" in text
    assert "gross pnl excludes costs" in text
    assert "safety notes" in text
    assert "------------" in text
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
    paths = write_paper_trading_report(
        session,
        tmp_path / "reports" / "empty",
        generated_at=_GENERATED_AT,
    )

    summary_payload = json.loads(paths.summary_json.read_text(encoding="utf-8"))
    orders_payload = json.loads(paths.orders_json.read_text(encoding="utf-8"))
    positions_payload = json.loads(paths.open_positions_json.read_text(encoding="utf-8"))
    exits_payload = json.loads(paths.exit_records_json.read_text(encoding="utf-8"))

    assert summary_payload["report_version"] == 1
    assert summary_payload["report_source"] == "paper"
    assert summary_payload["generated_at"] == _GENERATED_AT_ISO
    assert summary_payload["total_orders"] == 0
    assert summary_payload["closed_trades_count"] == 0
    assert summary_payload["exits_with_pnl_count"] == 0
    assert summary_payload["total_simulated_gross_pnl"] == 0
    assert summary_payload["total_estimated_costs"] == 0
    assert summary_payload["total_simulated_net_pnl"] == 0
    assert summary_payload["winning_exits_count"] == 0
    assert summary_payload["losing_exits_count"] == 0
    assert summary_payload["flat_exits_count"] == 0
    assert summary_payload["unknown_pnl_exits_count"] == 0
    assert summary_payload["net_winning_exits_count"] == 0
    assert summary_payload["net_losing_exits_count"] == 0
    assert summary_payload["net_flat_exits_count"] == 0
    assert summary_payload["unknown_net_pnl_exits_count"] == 0
    assert summary_payload["paper_pnl_is_simulation_only"] is True
    assert summary_payload["estimated_costs_included_in_net_pnl"] is True
    assert summary_payload["gross_pnl_excludes_costs"] is True
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
