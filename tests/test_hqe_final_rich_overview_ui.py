from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_rich_operator_theme_and_hero():
    text = source()
    assert "HQE_FINAL_RICH_OVERVIEW_V2" in text
    assert '"background": "#07111f"' in text
    assert '"accent": "#2dd4bf"' in text
    assert 'text="Daily Operator Center"' in text


def test_broker_surface_stays_off_overview():
    text = source()
    assert "HQE_OVERVIEW_CENTERED_ACTIONS_V1" in text
    assert "broker_panel.pack_forget()" in text
    assert 'text="Broker Connect Center"' in text
    assert "command=open_broker_connect_center" in text


def test_overview_is_wide_and_buttons_are_one_by_one():
    text = source()
    assert (
        "action_panel_width = min(820, max(620, "
        "int(window_width * 0.58)))"
    ) in text
    assert text.count('.pack(fill="x", padx=28, pady=7)') >= 12


def test_verbose_status_cards_are_hidden_only_on_overview():
    tree = ast.parse(source())
    hidden = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        call = node.value
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr in {
                "pack_forget",
                "grid_remove",
                "place_forget",
            }
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id.endswith("_panel")
        ):
            continue
        hidden += 1
    assert hidden >= 8


def test_permanent_safety_language_remains():
    text = source()
    assert "NO REAL ORDERS" in text
    assert "NO BROKER EXECUTION" in text
    assert "REAL TRADING LOCKED" in text
