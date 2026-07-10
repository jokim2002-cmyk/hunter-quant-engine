from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_market_data_quality_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("quality_center_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False


def test_app_contains_market_data_quality_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "data_quality_center_snapshot" in text
    assert "launch_cache_index_worker" in text
    assert "def refresh_market_data_quality_center" in text
    assert "def open_market_data_quality_center" in text
    assert "Market Data Quality Center" in text
    assert "Rebuild Cache Index" in text
    assert "Open Best Data File" in text
    assert "Provider Registry" in text
