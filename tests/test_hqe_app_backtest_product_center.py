from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_backtest_product_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("backtest_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["recorded_data_only"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False


def test_app_contains_backtest_product_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "backtest_center_snapshot" in text
    assert "preview_backtest_job" in text
    assert "def refresh_backtest_product_center" in text
    assert "def open_backtest_product_center" in text
    assert "Backtest Product Center" in text
    assert "Preview Backtest Job" in text
    assert "Save Backtest Job" in text
    assert "Run Guarded Backtest" in text
    assert "Open Latest Result Summary" in text
    assert "Equity / Drawdown Evidence" in text
