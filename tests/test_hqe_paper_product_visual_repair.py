from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"
HIDDEN = REPO / "scripts" / "hqe_hidden_paper_watch_supervisor.py"
RUNTIME = REPO / "scripts" / "hqe_paper_product_runtime.py"


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "hqe_paper_product_runtime_visual_repair",
        RUNTIME,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def app_source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def function_source(name: str) -> str:
    text = app_source()
    tree = ast.parse(text)
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]
    assert len(found) == 1
    return ast.get_source_segment(text, found[0]) or ""


def test_today_report_always_shows_actual_paper_status_and_pnl():
    text = function_source("show_report_page")
    for marker in (
        "Actual Paper Trading Position & P&L",
        '"Position"',
        '"Option symbol"',
        '"Latest price"',
        '"Unrealized P&L"',
        '"Realized P&L"',
        "Open Paper Ledger / History",
        "truthful empty state",
    ):
        assert marker in text


def test_recorded_replay_remains_separate_evidence():
    text = function_source("show_report_page")
    assert "Recorded Replay" in text
    assert "Separate Evaluation Evidence" in text
    assert "Evaluation only" in text
    assert "not a paper position" in text


def test_app_and_collector_prefer_pythonw_without_console():
    app = app_source()
    hidden = HIDDEN.read_text(encoding="utf-8-sig")

    assert "pythonw.exe" in app
    assert "DETACHED_PROCESS" in app
    assert "visible_terminal_created" in app

    assert "pythonw.exe" in hidden
    assert "CREATE_NO_WINDOW | DETACHED_PROCESS" in hidden
    assert '"visible_terminal_created": False' in hidden


def test_empty_workspace_snapshot_is_truthful_flat(tmp_path):
    module = load_runtime()
    snapshot = module.paper_product_snapshot(tmp_path)
    assert snapshot["position_status"] == "FLAT"
    assert snapshot["realized_paper_pnl"] == 0.0
    assert snapshot["paper_only"] is True
    assert snapshot["real_orders_allowed"] is False


def test_runtime_guard_declares_no_visible_terminal():
    module = load_runtime()
    guard = module.guard_payload()
    assert guard["no_visible_terminal"] is True
    assert guard["pythonw_runtime_supported"] is True
