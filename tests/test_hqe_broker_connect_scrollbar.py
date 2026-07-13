from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_broker_connect_has_right_side_vertical_scrollbar():
    text = source()
    assert "HQE_BROKER_CONNECT_SCROLL_V1" in text
    assert "broker_scrollbar = ttk.Scrollbar(" in text
    assert 'orient="vertical"' in text
    assert 'broker_scrollbar.pack(side="right", fill="y")' in text
    assert "command=broker_scroll_canvas.yview" in text


def test_broker_connect_content_uses_scroll_inner():
    text = source()
    assert "intro = page_card(\n            broker_scroll_inner," in text
    assert "grid = tk.Frame(\n            broker_scroll_inner," in text
    assert "broker_scroll_window = broker_scroll_canvas.create_window(" in text
    assert "window=broker_scroll_inner" in text


def test_broker_connect_scroll_region_and_mousewheel():
    text = source()
    assert "def _sync_broker_connect_scroll(" in text
    assert "scrollregion=bounds" in text
    assert "def _broker_connect_mousewheel(event):" in text
    assert "broker_scroll_canvas.yview_scroll(" in text
    assert "def _bind_broker_connect_scroll(widget)" in text


def test_guided_broker_button_remains_available():
    text = source()
    assert 'text="Open Guided Broker Connect"' in text
    assert "command=open_broker_connect_center" in text
