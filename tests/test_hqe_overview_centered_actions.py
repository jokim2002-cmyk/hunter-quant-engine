from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_overview_broker_surface_is_hidden():
    text = source()
    assert "HQE_OVERVIEW_CENTERED_ACTIONS_V1" in text
    assert "broker_panel.pack_forget()" in text


def test_daily_actions_are_centered_in_vertical_panel():
    text = source()
    assert "action_panel_width = min(820, max(620, int(window_width * 0.58)))" in text
    assert 'side="top"' in text
    assert 'anchor="center"' in text
    assert "expand=True" in text


def test_broker_connect_page_remains_available():
    text = source()
    assert "def show_broker_page() -> None:" in text
    assert 'text="Open Guided Broker Connect"' in text
    assert '"Broker Connect"' in text
