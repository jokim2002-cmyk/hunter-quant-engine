from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_app_uses_canonical_paper_product_runtime():
    text = source()
    assert "from hqe_paper_product_runtime import (" in text
    assert "hqe_paper_product_runtime.py" in text
    assert "paper_product_snapshot(workspace)" in text
    assert "RUNNING_CANONICAL_PAPER_RUNTIME" in text


def test_controller_no_longer_launches_legacy_runner():
    tree = ast.parse(source())
    controller = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "HiddenPaperWatchController"
    )
    controller_text = ast.get_source_segment(source(), controller) or ""
    assert "hqe_paper_product_runtime.py" in controller_text
    assert "hqe_market_day_persistent_paper_watch_loop.py" not in controller_text
    assert '"--stop"' in controller_text


def test_today_report_exposes_live_position_and_pnl_fields():
    text = source()
    required = (
        "Actual Paper Trading Position & P&L",
        '"Position"',
        '"Option symbol"',
        '"Latest price"',
        '"Unrealized P&L"',
        '"Realized P&L"',
        "Open Paper Ledger / History",
    )
    assert all(value in text for value in required)


def test_product_integration_keeps_real_execution_locked():
    text = source()
    assert '"broker_execution_invoked": False' in text
    assert '"order_api_invoked": False' in text
    assert '"auto_trading_invoked": False' in text
    assert '"real_money_invoked": False' in text
