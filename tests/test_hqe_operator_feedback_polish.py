from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def app_source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def nested_function(name: str) -> ast.FunctionDef:
    tree = ast.parse(app_source())
    run_gui = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_gui"
    )
    return next(
        node for node in ast.walk(run_gui)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_operator_busy_helpers_are_present():
    text = app_source()
    assert "def set_operator_busy(message: str) -> None:" in text
    assert "def clear_operator_busy(message: str) -> None:" in text
    assert "def show_safe_operation_error(" in text
    assert 'root.configure(cursor="watch")' in text


def test_long_operations_show_loading_feedback():
    for name in (
        "run_market_data_refresh",
        "run_safe_broker_data_test",
        "prepare_next_market_day_from_app",
    ):
        segment = ast.get_source_segment(app_source(), nested_function(name)) or ""
        assert "set_operator_busy(" in segment


def test_pollers_clear_loading_feedback():
    for name in (
        "poll_market_data_refresh",
        "poll_safe_broker_data_test",
        "poll_daily_startup_operation",
    ):
        segment = ast.get_source_segment(app_source(), nested_function(name)) or ""
        assert "clear_operator_busy(" in segment


def test_safe_error_message_preserves_execution_lock_language():
    text = app_source()
    assert "No real order was sent." in text
    assert "show_safe_operation_error('Market Data', 'Market-data refresh', exc)" in text
    assert "show_safe_operation_error('Safe Data Test', 'Safe broker data test', exc)" in text
    assert "show_safe_operation_error('Daily Startup', 'Next-day preparation', exc)" in text
