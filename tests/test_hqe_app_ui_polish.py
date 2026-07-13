from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_dpi_awareness_runs_before_tk_root():
    text = source()
    assert "def configure_windows_dpi_awareness() -> None:" in text
    assert text.index("    configure_windows_dpi_awareness()") < text.index("    root = tk.Tk()")


def test_adaptive_scaling_and_responsive_widths_are_present():
    text = source()
    assert "HQE_STABILIZATION_UI_POLISH_V1" in text
    assert 'root.tk.call("tk", "scaling", display_scaling)' in text
    assert "width=sidebar_width" in text
    assert "width=action_panel_width" in text


def test_single_main_window_minsize():
    tree = ast.parse(source())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "minsize"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "root"
    ]
    assert len(calls) == 1
