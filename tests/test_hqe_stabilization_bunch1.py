from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_stabilized_app_source_parses() -> None:
    ast.parse(source())


def test_main_action_panel_has_real_vertical_scroll() -> None:
    text = source()
    required = (
        "HQE_STABILIZATION_SCROLL_V1",
        "hqe_scroll_canvas",
        "hqe_scrollbar",
        'orient="vertical"',
        "yscrollcommand=hqe_scrollbar.set",
        "hqe_scroll_canvas.yview_scroll",
        'root.bind_all(\n        "<MouseWheel>"',
    )
    for marker in required:
        assert marker in text


def test_advanced_tools_always_has_direct_access() -> None:
    text = source()
    assert "HQE_STABILIZATION_MENU_V1" in text
    assert 'label="Tools"' in text
    assert 'label="Advanced Tools & Product Centers"' in text
    assert 'accelerator="Ctrl+T"' in text
    assert '"<Control-t>"' in text
    assert "command=open_advanced_tools_hub" in text


def test_startup_work_is_deferred_until_window_is_visible() -> None:
    text = source()
    assert "HQE_STABILIZATION_STARTUP_V1" in text
    assert 'show_page("Overview")\n    refresh_status_async()' in text
    assert "root.after(1200, lambda: refresh_daily_operations(False))" in text
    assert "root.after(1700, _deferred_fyers_startup)" in text
    assert "root.after(2400, lambda: refresh_broker_data_health(False))" in text
    assert "root.after(3100, lambda: refresh_market_data_center(False))" in text
    assert "\n    apply_stored_fyers_environment(overwrite=True)\n" not in text


def test_screen_aware_window_and_safety_language_remain() -> None:
    text = source()
    assert "HQE_STABILIZATION_GEOMETRY_V1" in text
    assert "root.winfo_screenwidth()" in text
    assert "root.winfo_screenheight()" in text
    assert "root.minsize(900, 600)" in text
    assert "Real trading controls are intentionally absent." in text
    assert "This app cannot place, modify or cancel broker orders." in text
