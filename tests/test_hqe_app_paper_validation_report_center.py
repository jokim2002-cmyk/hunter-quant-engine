from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_paper_validation_report_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("validation_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["paper_only"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False


def test_app_contains_validation_report_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "paper_validation_center_snapshot" in text
    assert "launch_report_pack_worker" in text
    assert "def refresh_paper_validation_report_center" in text
    assert "def open_paper_validation_report_center" in text
    assert "Paper Validation Intelligence" in text
    assert "Generate Report Pack" in text
    assert "Open Latest HTML Report" in text
    assert "Open Latest ZIP Pack" in text
    assert "No-Trade Reasons" in text
    assert "Strategy Drift" in text
    assert "Weekly Summary" in text
