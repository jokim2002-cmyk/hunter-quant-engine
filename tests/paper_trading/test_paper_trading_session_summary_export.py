import csv
import json
from pathlib import Path

from src.paper_trading.paper_trading_session_summary import PaperTradingSessionSummary
from src.paper_trading.paper_trading_session_summary_export import (
    format_paper_trading_session_summary,
    paper_trading_session_summary_to_dict,
    write_paper_trading_session_summary_csv,
    write_paper_trading_session_summary_json,
)


def _summary() -> PaperTradingSessionSummary:
    return PaperTradingSessionSummary(
        total_orders=2,
        open_positions_count=1,
        total_open_quantity=195,
        symbols=("NIFTY26JUL24200CE",),
    )


def test_paper_trading_session_summary_to_dict():
    payload = paper_trading_session_summary_to_dict(_summary())

    assert payload == {
        "total_orders": 2,
        "open_positions_count": 1,
        "total_open_quantity": 195,
        "symbols": ["NIFTY26JUL24200CE"],
        "has_open_positions": True,
    }


def test_format_paper_trading_session_summary_contains_safe_report_lines():
    text = format_paper_trading_session_summary(_summary()).lower()

    assert "paper trading session summary" in text
    assert "total orders: 2" in text
    assert "open positions count: 1" in text
    assert "total open quantity: 195" in text
    assert "symbols: nifty26jul24200ce" in text
    assert "has open positions: true" in text
    assert "local summary/export only" in text
    assert "no broker/fyers" in text
    assert "no live/real market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text


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


def test_write_paper_trading_session_summary_csv(tmp_path):
    output_path = tmp_path / "paper_session_summary.csv"

    written_path = write_paper_trading_session_summary_csv(_summary(), output_path)

    assert written_path == output_path

    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "total_orders": "2",
            "open_positions_count": "1",
            "total_open_quantity": "195",
            "symbols": "NIFTY26JUL24200CE",
            "has_open_positions": "True",
        }
    ]


def test_summary_export_source_has_no_external_order_execution_imports():
    source = Path(
        "src/paper_trading/paper_trading_session_summary_export.py"
    ).read_text(encoding="utf-8").lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
