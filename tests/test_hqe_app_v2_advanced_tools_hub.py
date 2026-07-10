from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def test_advanced_tools_hub_is_visible_and_complete():
    text = APP.read_text(encoding="utf-8-sig")
    ast.parse(text)

    required = (
        "def open_advanced_tools_hub",
        'text="Advanced Tools & Product Centers"',
        "advanced_tools_canvas",
        "advanced_tools_scrollbar",
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


def test_advanced_tools_hub_does_not_wrap_main_action_panel():
    text = APP.read_text(encoding="utf-8-sig")
    assert "action_panel_scroll_host" not in text
    assert "action_panel_canvas" not in text
    assert "action_panel_window_id" not in text
