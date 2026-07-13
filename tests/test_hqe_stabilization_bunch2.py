from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_global_callback_recovery_is_installed():
    text = source()
    assert "HQE_STABILIZATION_BUNCH2_CALLBACK_RECOVERY" in text
    assert "root.report_callback_exception = _hqe_report_callback_exception" in text
    assert 'log_file = log_dir / "hqe_ui_errors.log"' in text
    assert "no real order was sent" in text


def test_button_commands_are_not_string_callbacks():
    tree = ast.parse(source())
    failures = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "Button":
            continue
        for keyword in node.keywords:
            if keyword.arg == "command" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    failures.append(keyword.value.value)
    assert not failures, f"String button callbacks found: {failures}"


def test_callback_recovery_does_not_enable_execution():
    text = source()
    forbidden = (
        "real_orders_enabled = True",
        "broker_execution_enabled = True",
        "auto_trading_enabled = True",
        "order_api_hard_blocked = False",
    )
    assert not any(item in text for item in forbidden)
