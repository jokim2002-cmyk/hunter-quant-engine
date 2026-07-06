from __future__ import annotations

from pathlib import Path


def test_run_paper_trading_demo_smoke() -> None:
    script_path = Path("examples/run_paper_trading_demo.py")
    assert script_path.exists()

    # Import locally so this test stays offline and doesn't spawn processes.
    import importlib

    demo = importlib.import_module("examples.run_paper_trading_demo")

    rc = demo.run_demo()
    assert rc == 0


def test_demo_output_and_safety_constraints() -> None:
    import importlib
    import io
    import sys

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

    # Required messages
    assert "fake/local paper trading demo" in out
    assert "synthetic option-buy trade plan" in out
    assert "paper order id" in out
    assert "paper order symbol" in out
    assert "paper order quantity" in out
    assert "paper position" in out

    # Safety / no broker / no live market data / no real orders.
    assert "no broker/fyers" in out
    assert "no live/real market data" in out
    assert "no real orders placed" in out
    assert "not a profitability claim" in out

    # Must include values.
    assert "paper-" in out
    assert "nifty26jul24200ce" in out
    assert "paper position quantity" in out

    # Forbidden SDK string check: ensure demo doesn't reference FYERS.
    source = script_path.read_text(encoding="utf-8").lower()
    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source

    # No broker order execution method names.
    forbidden_tokens = ["place" + "_order", "send" + "_order", "execute" + "_order"]
    for token in forbidden_tokens:
        assert token not in source


