from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def function_node(
    tree: ast.AST,
    name: str,
) -> ast.FunctionDef:
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == name
    ]
    assert len(found) == 1
    return found[0]


def test_taskbar_identity_runs_before_tk_root():
    text = source()
    tree = ast.parse(text)
    run_gui = function_node(tree, "run_gui")
    segment = ast.get_source_segment(text, run_gui) or ""

    assert (
        "HQE_WINDOWS_TASKBAR_ICON_AND_ADVANCED_WHEEL_V1"
        in text
    )
    assert "SetCurrentProcessExplicitAppUserModelID" in text
    assert (
        segment.index("_configure_windows_taskbar_identity()")
        < segment.index("root = tk.Tk()")
    )


def test_main_window_icon_uses_tk_and_windows_message_paths():
    text = source()
    required = (
        "def _apply_hqe_window_icon",
        "window.iconbitmap(default=str(icon_path))",
        "user32.LoadImageW",
        "wm_seticon = 0x0080",
        "icon_small = 0",
        "icon_big = 1",
        "_apply_hqe_window_icon(root, icon)",
        "root.after_idle(",
    )
    missing = [marker for marker in required if marker not in text]
    assert not missing, "\n".join(missing)


def test_advanced_tools_wheel_is_bound_to_all_descendants():
    text = source()
    tree = ast.parse(text)
    hub = function_node(tree, "open_advanced_tools_hub")
    segment = ast.get_source_segment(text, hub) or ""

    required = (
        "def _bind_advanced_tools_mousewheel_tree",
        '"<MouseWheel>"',
        '"<Button-4>"',
        '"<Button-5>"',
        "_bind_advanced_tools_mousewheel_tree(child)",
        "_bind_advanced_tools_mousewheel_tree("
        "advanced_tools_dialog"
        ")",
    )
    missing = [marker for marker in required if marker not in segment]
    assert not missing, "\n".join(missing)


def test_wheel_supports_standard_and_high_resolution_deltas():
    text = source()
    assert 'getattr(event, "delta", 0)' in text
    assert "steps = max(1, abs(delta) // 120)" in text
    assert "-steps if delta > 0 else steps" in text


def test_ui_fix_does_not_add_execution_calls():
    text = source()
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
    )
    assert not any(marker in text for marker in forbidden)
