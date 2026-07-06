from __future__ import annotations

import importlib
import io
import json
import sys
from pathlib import Path


def test_run_paper_trading_demo_smoke() -> None:
    script_path = Path("examples/run_paper_trading_demo.py")
    assert script_path.exists()

    # Import locally so this test stays offline and does not spawn processes.
    demo = importlib.import_module("examples.run_paper_trading_demo")

    rc = demo.run_demo()
    assert rc == 0


def test_demo_output_and_safety_constraints() -> None:
    script_path = Path("examples/run_paper_trading_demo.py")
    demo = importlib.import_module("examples.run_paper_trading_demo")

    buf = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        rc = demo.run_demo()
    finally:
        sys.stdout = old_stdout

    out = buf.getvalue().lower()
    assert rc == 0

    # Required demo messages.
    assert "fake/local paper trading demo" in out
    assert "synthetic option-buy trade plan" in out
    assert "paper order id" in out
    assert "paper order symbol" in out
    assert "paper order quantity" in out
    assert "paper position symbol before close" in out
    assert "paper position quantity before close" in out

    # Close-position demo messages.
    assert "paper close result: closed" in out
    assert "paper exit id: paper-exit-000001" in out
    assert "paper close symbol: nifty26jul24200ce" in out
    assert "paper close quantity" in out
    assert "paper position after close: none" in out

    # Paper-only simulated P&L messages.
    assert "paper simulated exit price: 135.0" in out
    assert "paper simulated points: 35.0" in out
    assert "paper simulated gross pnl: 4550.0" in out
    assert "paper pnl is simulation only" in out
    assert "charges and slippage are not included" in out

    # Summary before close.
    assert "session summary total orders before close: 1" in out
    assert "session summary open positions before close: 1" in out
    assert "session summary total open quantity before close" in out
    assert "session summary symbols before close: nifty26jul24200ce" in out

    # Summary after close.
    assert "session summary total orders after close: 1" in out
    assert "session summary open positions after close: 0" in out
    assert "session summary total open quantity after close: 0" in out
    assert "session summary symbols after close: none" in out

    # Local report writer output.
    assert "paper report output dir:" in out
    assert "paper report summary json:" in out
    assert "paper report summary csv:" in out
    assert "paper report orders json:" in out
    assert "paper report orders csv:" in out
    assert "paper report open positions json:" in out
    assert "paper report open positions csv:" in out
    assert "paper report exit records json:" in out
    assert "paper report exit records csv:" in out
    assert "paper report text:" in out
    assert "paper report files are local/generated" in out

    # Safety / no broker / no live market data / no real orders.
    assert "no broker/fyers" in out
    assert "no live/real market data" in out
    assert "no real orders placed" in out
    assert "not a profitability claim" in out

    # Must include values.
    assert "paper-" in out
    assert "nifty26jul24200ce" in out

    # Forbidden SDK import check: safety text may mention FYERS, imports must not.
    source = script_path.read_text(encoding="utf-8").lower()
    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source

    # No broker order execution method names.
    forbidden_tokens = ["place" + "_order", "send" + "_order", "execute" + "_order"]
    for token in forbidden_tokens:
        assert token not in source


def test_demo_writes_local_report_files_under_reports() -> None:
    demo = importlib.import_module("examples.run_paper_trading_demo")

    rc = demo.run_demo()

    assert rc == 0

    output_dir = Path("reports") / "paper_trading"
    expected_files = [
        output_dir / "summary.json",
        output_dir / "summary.csv",
        output_dir / "orders.json",
        output_dir / "orders.csv",
        output_dir / "open_positions.json",
        output_dir / "open_positions.csv",
        output_dir / "exit_records.json",
        output_dir / "exit_records.csv",
        output_dir / "report.txt",
    ]

    for path in expected_files:
        assert path.exists()
        assert "reports" in [part.lower() for part in path.parts]

    summary_payload = json.loads(
        (output_dir / "summary.json").read_text(encoding="utf-8")
    )
    exit_records_payload = json.loads(
        (output_dir / "exit_records.json").read_text(encoding="utf-8")
    )
    report_text = (output_dir / "report.txt").read_text(encoding="utf-8").lower()

    assert summary_payload["total_orders"] == 1
    assert summary_payload["open_positions_count"] == 0
    assert summary_payload["total_open_quantity"] == 0
    assert summary_payload["symbols"] == []
    assert summary_payload["has_open_positions"] is False

    assert len(exit_records_payload) == 1
    assert exit_records_payload[0]["exit_id"] == "PAPER-EXIT-000001"
    assert exit_records_payload[0]["symbol"] == "NIFTY26JUL24200CE"
    assert exit_records_payload[0]["simulated_points"] == 35.0
    assert exit_records_payload[0]["simulated_gross_pnl"] == 4550.0

    assert "paper pnl is simulation only" in report_text
    assert "charges and slippage are not included" in report_text
    assert "not a profitability claim" in report_text
