from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"
HELPER = REPO / "scripts" / "hqe_paper_watch_auth_readiness_gate.py"


def function_source(text: str, name: str) -> str:
    tree = ast.parse(text)
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]
    assert len(found) == 1
    return ast.get_source_segment(text, found[0]) or ""


def test_verified_gate_overrides_stale_watch_status():
    text = APP.read_text(encoding="utf-8-sig")
    source = function_source(
        text,
        "apply_paper_watch_auth_gate",
    )

    assert 'if gate["allowed"]:' in source
    assert 'card_vars["broker"].set(gate["broker_card"])' in source
    assert 'card_vars["data"].set(gate["data_card"])' in source
    assert 'card_vars["watch"].set(' in source
    assert 'gate["watch_card_running"]' in source
    assert 'gate["watch_card"]' in source
    assert "Paper Watch is ready but not running." in source


def test_helper_has_truthful_verified_card_labels():
    text = HELPER.read_text(encoding="utf-8-sig")
    required = (
        '"broker_card": "Fyers: DATA-ONLY AUTH VERIFIED"',
        '"data_card": "CURRENT-DAY DATA PATH VERIFIED"',
        '"watch_card": "READY TO START"',
        '"watch_card_running": "RUNNING WITH VERIFIED DATA PATH"',
    )
    assert all(marker in text for marker in required)


def test_refresh_paths_apply_gate_after_base_status():
    text = APP.read_text(encoding="utf-8-sig")
    refresh = function_source(text, "refresh_status")
    async_refresh = function_source(
        text,
        "refresh_status_async",
    )

    assert (
        "apply_paper_watch_auth_gate(show_warning=True)"
        in refresh
    )
    assert (
        "apply_paper_watch_auth_gate(show_warning=True)"
        in async_refresh
    )


def test_no_execution_controls_added():
    text = APP.read_text(encoding="utf-8-sig")
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)
