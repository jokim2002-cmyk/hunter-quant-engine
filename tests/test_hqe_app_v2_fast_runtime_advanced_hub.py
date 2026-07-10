from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"

ADVANCED_REFRESH_NAMES = {
    "refresh_operator_dashboard",
    "refresh_market_data_quality_center",
    "refresh_strategy_pack_center",
    "refresh_strategy_builder_center",
    "refresh_backtest_product_center",
    "refresh_session_history_center",
    "refresh_paper_validation_report_center",
    "refresh_release_center",
    "refresh_rc_audit_center",
    "refresh_operator_acceptance_center",
}


def find_run_gui(tree: ast.AST) -> ast.FunctionDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_gui"
    ]
    assert len(matches) == 1
    return matches[0]


def is_direct_root_after(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Expr):
        return False
    call = statement.value
    if not isinstance(call, ast.Call):
        return False
    function = call.func
    return (
        isinstance(function, ast.Attribute)
        and function.attr == "after"
        and isinstance(function.value, ast.Name)
        and function.value.id == "root"
    )


def test_advanced_hub_runtime_markers_and_centers():
    text = APP.read_text(encoding="utf-8-sig")
    ast.parse(text)

    required = (
        "def open_advanced_tools_hub",
        "HQE_ADVANCED_TOOLS_SMOKE_PASS",
        "advanced_tools_dialog.update_idletasks()",
        "Operator Dashboard",
        "Market Data Quality Center",
        "Strategy Pack Center",
        "Strategy Builder & Selector",
        "Backtest Product Center",
        "Session History",
        "Paper Validation Intelligence",
        "Windows Release Center",
        "Final RC Audit & Freeze",
        "Operator Acceptance & RC Sign-Off",
    )
    missing = [marker for marker in required if marker not in text]
    assert not missing, "\n".join(missing)


def test_windows_child_processes_are_hidden():
    text = APP.read_text(encoding="utf-8-sig")
    required = (
        "class _HQEHiddenPopen",
        "subprocess.CREATE_NO_WINDOW",
        "subprocess.Popen = _HQEHiddenPopen",
        "_hqe_hidden_popen_installed",
    )
    missing = [marker for marker in required if marker not in text]
    assert not missing, "\n".join(missing)


def test_advanced_centers_are_not_eagerly_scheduled_at_startup():
    text = APP.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    run_gui = find_run_gui(tree)

    failures: list[str] = []
    for statement in run_gui.body:
        # Only direct run_gui startup scheduling counts here.
        # root.after calls inside dialog polling functions are legitimate
        # and run only after the operator opens that center.
        if not is_direct_root_after(statement):
            continue
        rendered = ast.unparse(statement)
        if any(
            name in rendered
            for name in ADVANCED_REFRESH_NAMES
        ):
            failures.append(rendered)

    assert not failures, "\n\n".join(failures)


def test_backtest_dialog_polling_is_allowed_after_open():
    text = APP.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    run_gui = find_run_gui(tree)

    backtest = next(
        node
        for node in run_gui.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "open_backtest_product_center"
    )
    rendered = ast.unparse(backtest)
    assert "root.after(1200, poll_backtest)" in rendered
    assert "refresh_backtest_product_center(False)" in rendered


def test_callback_errors_are_visible_and_logged():
    text = APP.read_text(encoding="utf-8-sig")
    required = (
        "def _hqe_report_callback_exception",
        "root.report_callback_exception",
        "HQE_UI_CALLBACK_ERROR.txt",
        "messagebox.showerror",
    )
    missing = [marker for marker in required if marker not in text]
    assert not missing, "\n".join(missing)


def test_main_action_panel_is_not_canvas_wrapped():
    text = APP.read_text(encoding="utf-8-sig")
    assert "action_panel_scroll_host" not in text
    assert "action_panel_window_id" not in text

def test_backtest_hub_callback_is_deferred_until_click():
    text = APP.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    run_gui = find_run_gui(tree)

    backtest_def = next(
        node
        for node in run_gui.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "open_backtest_product_center"
    )

    unsafe_direct_references: list[str] = []
    deferred_found = False

    for node in ast.walk(run_gui):
        if not isinstance(node, ast.keyword):
            continue
        if node.arg != "command":
            continue

        value = node.value
        if (
            isinstance(value, ast.Name)
            and value.id == "open_backtest_product_center"
            and value.lineno < backtest_def.lineno
        ):
            unsafe_direct_references.append(
                f"line {value.lineno}"
            )

        if isinstance(value, ast.Lambda):
            rendered = ast.unparse(value)
            if (
                "open_backtest_product_center()"
                in rendered
            ):
                deferred_found = True

    assert not unsafe_direct_references, (
        "Backtest callback is read before its nested function "
        "definition: "
        + ", ".join(unsafe_direct_references)
    )
    assert deferred_found
