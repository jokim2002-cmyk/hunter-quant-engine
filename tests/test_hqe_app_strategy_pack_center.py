from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_strategy_pack_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("strategy_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["json_only"] is True
    assert payload["paper_only"] is True
    assert payload["real_orders_enabled"] is False


def test_app_contains_strategy_pack_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "strategy_pack_center_snapshot" in text
    assert "def refresh_strategy_pack_center" in text
    assert "def open_strategy_pack_center" in text
    assert "Strategy Pack Center" in text
    assert "Import Strategy Pack" in text
    assert "Export Selected Pack" in text
    assert "Clone Selected as Draft" in text
    assert "Locked Validation Candidate" in text
