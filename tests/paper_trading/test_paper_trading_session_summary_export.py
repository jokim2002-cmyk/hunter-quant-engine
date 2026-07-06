import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.paper_trading.paper_order_journal import PaperOrderRequest
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.paper_trading_session import PaperTradingSession
from src.paper_trading.paper_trading_session_summary import (
    PaperTradingSessionSummary,
    build_paper_trading_session_summary,
)
from src.paper_trading.paper_trading_session_summary_export import (
    format_paper_trading_session_summary,
    paper_trading_session_summary_to_csv_row,
    paper_trading_session_summary_to_dict,
    write_paper_trading_session_summary_csv,
    write_paper_trading_session_summary_json,
)


_OPENED_AT = datetime(2026, 7, 6, 9, 15, tzinfo=timezone.utc)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30, tzinfo=timezone.utc)


def _summary() -> PaperTradingSessionSummary:
    return PaperTradingSessionSummary(
        total_orders=2,
        open_positions_count=1,
        total_open_quantity=195,
        symbols=("NIFTY26JUL24200CE",),
    )


def _closed_summary() -> PaperTradingSessionSummary:
    session = PaperTradingSession()
    session.submit_order(
        PaperOrderRequest(
            symbol="NIFTY26JUL24200CE",
            quantity=65,
            planned_entry_price=100.0,
            created_at=_OPENED_AT,
        )
    )
    session.close_position("NIFTY26JUL24200CE")

    return build_paper_trading_session_summary(session)


def _pnl_summary() -> PaperTradingSessionSummary:
    session = PaperTradingSession()
    session.submit_order(
        PaperOrderRequest(
            symbol="NIFTY26JUL24200CE",
            quantity=130,
            planned_entry_price=100.0,
            created_at=_OPENED_AT,
        )
    )
    session.close_position_with_exit_record(
        "NIFTY26JUL24200CE",
        closed_at=_CLOSED_AT,
        exit_reason=PaperExitReason.TARGET,
        exit_price=135.0,
        estimated_exit_charges=40.0,
        estimated_slippage=13.0,
    )

    return build_paper_trading_session_summary(session)


def test_paper_trading_session_summary_to_dict():
    payload = paper_trading_session_summary_to_dict(_summary())

    assert payload == {
        "total_orders": 2,
        "open_positions_count": 1,
        "total_open_quantity": 195,
        "symbols": ["NIFTY26JUL24200CE"],
        "has_open_positions": True,
        "closed_trades_count": 0,
        "has_closed_trades": False,
        "exits_with_pnl_count": 0,
        "total_simulated_gross_pnl": 0.0,
        "total_estimated_costs": 0.0,
        "total_simulated_net_pnl": 0.0,
        "winning_exits_count": 0,
        "losing_exits_count": 0,
        "flat_exits_count": 0,
        "unknown_pnl_exits_count": 0,
        "net_winning_exits_count": 0,
        "net_losing_exits_count": 0,
        "net_flat_exits_count": 0,
        "unknown_net_pnl_exits_count": 0,
        "paper_pnl_is_simulation_only": True,
        "estimated_costs_included_in_net_pnl": True,
        "gross_pnl_excludes_costs": True,
    }


def test_paper_trading_session_summary_to_dict_after_closed_position():
    payload = paper_trading_session_summary_to_dict(_closed_summary())

    assert payload["total_orders"] == 1
    assert payload["open_positions_count"] == 0
    assert payload["total_open_quantity"] == 0
    assert payload["symbols"] == []
    assert payload["has_open_positions"] is False
    assert payload["closed_trades_count"] == 0
    assert payload["total_simulated_gross_pnl"] == 0
    assert payload["total_simulated_net_pnl"] == 0


def test_paper_trading_session_summary_to_dict_after_pnl_exit():
    payload = paper_trading_session_summary_to_dict(_pnl_summary())

    assert payload["total_orders"] == 1
    assert payload["open_positions_count"] == 0
    assert payload["closed_trades_count"] == 1
    assert payload["has_closed_trades"] is True
    assert payload["exits_with_pnl_count"] == 1
    assert payload["total_simulated_gross_pnl"] == 4550.0
    assert payload["total_estimated_costs"] == 53.0
    assert payload["total_simulated_net_pnl"] == 4497.0
    assert payload["winning_exits_count"] == 1
    assert payload["net_winning_exits_count"] == 1
    assert payload["paper_pnl_is_simulation_only"] is True


def test_paper_trading_session_summary_to_csv_row():
    payload = paper_trading_session_summary_to_csv_row(_summary())

    assert payload["symbols"] == "NIFTY26JUL24200CE"
    assert payload["closed_trades_count"] == 0
    assert payload["total_simulated_gross_pnl"] == 0.0
    assert payload["total_simulated_net_pnl"] == 0.0


def test_format_paper_trading_session_summary_contains_safe_report_lines():
    text = format_paper_trading_session_summary(_summary()).lower()

    assert "paper trading session summary" in text
    assert "total orders: 2" in text
    assert "open positions count: 1" in text
    assert "total open quantity: 195" in text
    assert "symbols: nifty26jul24200ce" in text
    assert "has open positions: true" in text
    assert "paper trading p&l summary" in text
    assert "closed trades count: 0" in text
    assert "total simulated gross pnl: 0.0" in text
    assert "total simulated net pnl: 0.0" in text
    assert "paper pnl is simulation only" in text
    assert "estimated costs are included in net pnl only" in text
    assert "gross pnl excludes costs" in text
    assert "local summary/export only" in text
    assert "no broker/fyers" in text
    assert "no live/real market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text


def test_format_pnl_summary_contains_net_pnl_lines():
    text = format_paper_trading_session_summary(_pnl_summary()).lower()

    assert "closed trades count: 1" in text
    assert "exits with pnl count: 1" in text
    assert "total simulated gross pnl: 4550.0" in text
    assert "total estimated costs: 53.0" in text
    assert "total simulated net pnl: 4497.0" in text
    assert "winning exits count: 1" in text
    assert "net winning exits count: 1" in text


def test_format_empty_symbols_summary_uses_none():
    summary = PaperTradingSessionSummary(
        total_orders=0,
        open_positions_count=0,
        total_open_quantity=0,
        symbols=(),
    )

    text = format_paper_trading_session_summary(summary).lower()

    assert "symbols: none" in text
    assert "has open positions: false" in text


def test_format_closed_position_summary_uses_none_symbols():
    text = format_paper_trading_session_summary(_closed_summary()).lower()

    assert "total orders: 1" in text
    assert "open positions count: 0" in text
    assert "total open quantity: 0" in text
    assert "symbols: none" in text
    assert "has open positions: false" in text
    assert "closed trades count: 0" in text


def test_write_paper_trading_session_summary_json(tmp_path):
    output_path = tmp_path / "paper_session_summary.json"

    written_path = write_paper_trading_session_summary_json(_summary(), output_path)

    assert written_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["total_orders"] == 2
    assert payload["open_positions_count"] == 1
    assert payload["total_open_quantity"] == 195
    assert payload["symbols"] == ["NIFTY26JUL24200CE"]
    assert payload["has_open_positions"] is True
    assert payload["closed_trades_count"] == 0
    assert payload["total_simulated_gross_pnl"] == 0
    assert payload["total_simulated_net_pnl"] == 0


def test_write_closed_position_summary_json(tmp_path):
    output_path = tmp_path / "paper_closed_session_summary.json"

    written_path = write_paper_trading_session_summary_json(
        _closed_summary(),
        output_path,
    )

    assert written_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["total_orders"] == 1
    assert payload["open_positions_count"] == 0
    assert payload["total_open_quantity"] == 0
    assert payload["symbols"] == []
    assert payload["has_open_positions"] is False
    assert payload["closed_trades_count"] == 0


def test_write_pnl_summary_json(tmp_path):
    output_path = tmp_path / "paper_pnl_session_summary.json"

    written_path = write_paper_trading_session_summary_json(
        _pnl_summary(),
        output_path,
    )

    assert written_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["closed_trades_count"] == 1
    assert payload["total_simulated_gross_pnl"] == 4550.0
    assert payload["total_estimated_costs"] == 53.0
    assert payload["total_simulated_net_pnl"] == 4497.0


def test_write_paper_trading_session_summary_csv(tmp_path):
    output_path = tmp_path / "paper_session_summary.csv"

    written_path = write_paper_trading_session_summary_csv(_summary(), output_path)

    assert written_path == output_path

    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["total_orders"] == "2"
    assert rows[0]["open_positions_count"] == "1"
    assert rows[0]["total_open_quantity"] == "195"
    assert rows[0]["symbols"] == "NIFTY26JUL24200CE"
    assert rows[0]["has_open_positions"] == "True"
    assert rows[0]["closed_trades_count"] == "0"
    assert rows[0]["total_simulated_gross_pnl"] == "0.0"
    assert rows[0]["total_simulated_net_pnl"] == "0.0"


def test_write_closed_position_summary_csv(tmp_path):
    output_path = tmp_path / "paper_closed_session_summary.csv"

    written_path = write_paper_trading_session_summary_csv(
        _closed_summary(),
        output_path,
    )

    assert written_path == output_path

    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["total_orders"] == "1"
    assert rows[0]["open_positions_count"] == "0"
    assert rows[0]["total_open_quantity"] == "0"
    assert rows[0]["symbols"] == ""
    assert rows[0]["has_open_positions"] == "False"
    assert rows[0]["closed_trades_count"] == "0"


def test_write_pnl_summary_csv(tmp_path):
    output_path = tmp_path / "paper_pnl_session_summary.csv"

    written_path = write_paper_trading_session_summary_csv(
        _pnl_summary(),
        output_path,
    )

    assert written_path == output_path

    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["closed_trades_count"] == "1"
    assert rows[0]["total_simulated_gross_pnl"] == "4550.0"
    assert rows[0]["total_estimated_costs"] == "53.0"
    assert rows[0]["total_simulated_net_pnl"] == "4497.0"


def test_summary_export_source_has_no_external_order_execution_imports():
    source = Path(
        "src/paper_trading/paper_trading_session_summary_export.py"
    ).read_text(encoding="utf-8").lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
