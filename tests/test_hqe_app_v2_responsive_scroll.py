from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def test_right_action_panel_has_responsive_scrolling():
    text = APP.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    required = (
        "action_panel_scroll_host",
        "action_panel_canvas",
        "action_panel_scrollbar",
        "action_panel_window_id",
        "def _hqe_sync_action_panel_scroll",
        "def _hqe_action_panel_mousewheel",
        'orient="vertical"',
        "scrollregion",
        "winfo_reqheight",
        "winfo_height",
        "pack_forget",
        "<MouseWheel>",
    )
    missing = [marker for marker in required if marker not in text]
    assert not missing, "\n".join(missing)

    assert any(
        isinstance(node, ast.FunctionDef)
        and node.name == "_hqe_sync_action_panel_scroll"
        for node in ast.walk(tree)
    )
