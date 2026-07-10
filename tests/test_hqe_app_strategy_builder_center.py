from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_strategy_builder_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("strategy_builder_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["paper_selection_only"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False


def test_app_contains_strategy_builder_selector():
    text = APP.read_text(encoding="utf-8-sig")
    assert "builder_center_snapshot" in text
    assert "build_strategy_preview" in text
    assert "def refresh_strategy_builder_center" in text
    assert "def open_strategy_builder_center" in text
    assert "Strategy Builder & Selector" in text
    assert "Preview Strategy" in text
    assert "Save as Draft" in text
    assert "Select for Paper Validation" in text
    assert "Clear Active Selection" in text
