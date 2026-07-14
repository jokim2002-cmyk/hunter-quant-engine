from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
HELPER = SCRIPTS / "hqe_paper_watch_auth_readiness_gate.py"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load_helper():
    scripts = str(SCRIPTS)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    name = "hqe_paper_watch_auth_readiness_gate_test"
    spec = importlib.util.spec_from_file_location(name, HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ready_auth():
    return {
        "status": "READY",
        "access_token_present": True,
    }


def test_current_day_auth_required_blocks_start(tmp_path):
    module = load_helper()
    gate = module.paper_watch_auth_gate(
        tmp_path,
        now=date(2026, 7, 14),
        auth_snapshot=ready_auth(),
        workflow_snapshot={
            "status": "AUTH_REQUIRED",
            "stage": "OPTION_CHAIN",
            "trading_date": "2026-07-14",
            "message": "Please provide valid token",
        },
    )

    assert gate["allowed"] is False
    assert gate["state"] == "AUTH_REQUIRED"
    assert "TOKEN REFRESH REQUIRED" in gate["broker_card"]
    assert "NO FRESH DATA" in gate["data_card"]
    assert "START BLOCKED" in gate["watch_card"]


def test_stored_token_without_today_proof_is_blocked(tmp_path):
    module = load_helper()
    gate = module.paper_watch_auth_gate(
        tmp_path,
        now=date(2026, 7, 14),
        auth_snapshot=ready_auth(),
        workflow_snapshot={
            "status": "COMPLETE",
            "trading_date": "2026-07-13",
        },
    )

    assert gate["allowed"] is False
    assert gate["state"] == "TOKEN_NOT_VERIFIED_TODAY"


def test_current_day_complete_allows_paper_watch(tmp_path):
    module = load_helper()
    gate = module.paper_watch_auth_gate(
        tmp_path,
        now=date(2026, 7, 14),
        auth_snapshot=ready_auth(),
        workflow_snapshot={
            "status": "COMPLETE",
            "stage": "COMPLETE",
            "trading_date": "2026-07-14",
        },
    )

    assert gate["allowed"] is True
    assert gate["state"] == "AUTH_AND_DATA_PATH_VERIFIED"
    assert gate["real_orders_allowed"] is False


def test_missing_secure_token_is_blocked(tmp_path):
    module = load_helper()
    gate = module.paper_watch_auth_gate(
        tmp_path,
        now=date(2026, 7, 14),
        auth_snapshot={
            "status": "NOT_READY",
            "access_token_present": False,
        },
        workflow_snapshot={
            "status": "COMPLETE",
            "trading_date": "2026-07-14",
        },
    )

    assert gate["allowed"] is False
    assert gate["state"] == "SECURE_TOKEN_MISSING"


def test_app_has_visible_warning_and_blocks_both_start_paths():
    text = APP.read_text(encoding="utf-8-sig")
    helper_text = HELPER.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    app_required = (
        "paper_watch_auth_gate",
        "def apply_paper_watch_auth_gate",
        "if not gate[\"allowed\"]:",
    )
    app_missing = [
        marker for marker in app_required if marker not in text
    ]
    assert not app_missing, "\n".join(app_missing)

    helper_required = (
        "Fyers Token Refresh Required",
        "Fresh market data and Start Paper Watch remain blocked",
        "PROCESS RUNNING",
        "FRESH DATA BLOCKED",
    )
    helper_missing = [
        marker
        for marker in helper_required
        if marker not in helper_text
    ]
    assert not helper_missing, "\n".join(helper_missing)

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    ]
    start_watch = next(
        node for node in functions if node.name == "start_watch"
    )
    run_operation = next(
        node
        for node in functions
        if node.name == "run_paper_watch_operation"
    )

    start_source = ast.get_source_segment(text, start_watch) or ""
    operation_source = ast.get_source_segment(text, run_operation) or ""

    assert "paper_watch_auth_gate(workspace)" in start_source
    assert "controller.start()" in start_source
    assert start_source.index("if not gate") < start_source.index(
        "controller.start()"
    )

    assert 'operation.lower() == "start"' in operation_source
    assert "paper_watch_auth_gate(workspace)" in operation_source
    assert operation_source.index("if not gate") < operation_source.index(
        "launch_watch_control_worker"
    )
