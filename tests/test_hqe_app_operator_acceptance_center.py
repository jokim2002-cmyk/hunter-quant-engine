from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_operator_acceptance_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("acceptance_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["read_only_acceptance"] is True
    assert payload["new_product_features"] is False
    assert payload["real_orders_enabled"] is False


def test_app_contains_operator_acceptance_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "operator_acceptance_center_snapshot" in text
    assert "launch_operator_acceptance" in text
    assert "def refresh_operator_acceptance_center" in text
    assert "def open_operator_acceptance_center" in text
    assert "Operator Acceptance & RC Sign-Off" in text
    assert "Run Operator Acceptance Dry Run" in text
    assert "Open Acceptance HTML" in text
    assert "Open Acceptance JSON" in text
    assert "Open Operator Guide" in text
