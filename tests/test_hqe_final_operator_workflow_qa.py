from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"
SMOKE = REPO / "scripts" / "hqe_final_operator_workflow_smoke.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def run_gui_node() -> ast.FunctionDef:
    tree = ast.parse(source())
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_gui"
    )


def test_all_main_operator_buttons_have_callbacks():
    gui = run_gui_node()
    button_calls = []
    for node in ast.walk(gui):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "Button":
            button_calls.append(node)
    assert len(button_calls) >= 20
    missing = []
    for call in button_calls:
        command = next(
            (item for item in call.keywords if item.arg == "command"),
            None,
        )
        if command is None:
            missing.append(call.lineno)
    assert not missing, f"Buttons missing commands at lines: {missing}"


def test_primary_operator_pages_and_callbacks_exist():
    text = source()
    required = (
        "show_overview_page",
        "show_broker_page",
        "show_paper_watch_page",
        "show_report_page",
        "show_safety_page",
        "refresh_status_async",
        "start_watch",
        "stop_watch",
        "open_report",
        "open_latest_evidence",
        "run_market_data_refresh",
        "run_safe_broker_data_test",
        "prepare_next_market_day_from_app",
    )
    for name in required:
        assert f"def {name}(" in text


def test_callback_recovery_and_safe_feedback_remain():
    text = source()
    assert "root.report_callback_exception" in text
    assert "No real order was sent." in text
    assert 'root.configure(cursor="watch")' in text
    assert "refresh_status_async()" in text


def test_final_operator_smoke_passes():
    spec = importlib.util.spec_from_file_location("hqe_final_smoke", SMOKE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.workflow_smoke()
    assert payload["status"] == "PASS"
    assert payload["real_order_invoked"] is False
    assert payload["broker_execution_invoked"] is False
