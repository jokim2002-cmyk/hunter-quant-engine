from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_release_candidate_audit_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("rc_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["audit_mode"] == (
        "READ_ONLY_SNAPSHOTS_AND_GUARDS"
    )
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False


def test_app_contains_final_rc_audit_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "rc_audit_center_snapshot" in text
    assert "launch_rc_audit_worker" in text
    assert "def refresh_rc_audit_center" in text
    assert "def open_rc_audit_center" in text
    assert "Final RC Audit & Freeze" in text
    assert "Run End-to-End RC Audit" in text
    assert "Open Latest Audit Report" in text
    assert "Open Freeze Manifest" in text
    assert "Open Operator Guide" in text
