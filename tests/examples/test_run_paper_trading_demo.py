from __future__ import annotations

import importlib
import io
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
    assert "paper close symbol: nifty26jul24200ce" in out
    assert "paper close quantity" in out
    assert "paper position after close: none" in out

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
