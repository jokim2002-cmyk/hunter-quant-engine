from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "scripts" / "hqe_product_app_v2.py"


def source() -> str:
    return APP.read_text(encoding="utf-8-sig")


def test_full_center_smoke_is_installed():
    text = source()
    assert "HQE_STABILIZATION_BUNCH3_FULL_CENTER_SMOKE" in text
    assert 'os.environ.get("HQE_FULL_CENTER_SMOKE") == "1"' in text
    assert "HQE_FULL_CENTER_SMOKE_PASS" in text


def test_dialog_backgrounds_use_safe_palette_fallback():
    text = source()
    assert 'palette["bg"]' not in text
    assert 'palette.get("bg", palette.get("app_bg", "#0b1220"))' in text


def test_cache_index_callback_is_defined():
    text = source()
    assert "def rebuild_market_data_cache_index() -> None:" in text
    assert "launch_cache_index_worker(repo_root(), workspace)" in text


def test_smoke_keeps_execution_locked():
    text = source()
    forbidden = (
        "real_orders_enabled = True",
        "broker_execution_enabled = True",
        "auto_trading_enabled = True",
        "order_api_hard_blocked = False",
    )
    assert not any(item in text for item in forbidden)
