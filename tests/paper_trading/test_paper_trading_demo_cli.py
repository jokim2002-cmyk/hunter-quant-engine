from __future__ import annotations

import importlib
import io
import runpy
import sys
from pathlib import Path


def _capture_stdout(func):
    buf = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        result = func()
    finally:
        sys.stdout = old_stdout

    return result, buf.getvalue().lower()


def test_paper_trading_demo_cli_main_returns_zero_and_prints_safety_lines():
    cli = importlib.import_module("src.paper_trading.paper_trading_demo_cli")

    rc, out = _capture_stdout(cli.main)

    assert rc == 0
    assert "fake/local paper trading demo" in out
    assert "synthetic option-buy trade plan" in out
    assert "paper trade symbol: nifty26jul24200ce" in out
    assert "paper trade quantity: 130" in out
    assert "paper simulated gross pnl: 4550.0" in out
    assert "paper estimated costs: 53.0" in out
    assert "paper simulated net pnl: 4497.0" in out
    assert "paper report output dir:" in out
    assert "paper report text:" in out
    assert "paper pnl is simulation only" in out
    assert "no broker/fyers" in out
    assert "no live/real market data" in out
    assert "no real orders placed" in out
    assert "not a profitability claim" in out


def test_paper_trading_demo_cli_can_run_as_module_command():
    sys.modules.pop("src.paper_trading.paper_trading_demo_cli", None)

    buf = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        try:
            runpy.run_module(
                "src.paper_trading.paper_trading_demo_cli",
                run_name="__main__",
            )
        except SystemExit as exc:
            assert exc.code == 0
    finally:
        sys.stdout = old_stdout

    out = buf.getvalue().lower()

    assert "fake/local paper trading demo" in out
    assert "paper report files are local/generated" in out
    assert "no real orders placed" in out


def test_paper_trading_demo_cli_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_demo_cli.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
