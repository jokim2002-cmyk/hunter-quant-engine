from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_release_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_app_center_guard_locks_execution():
    module = load("release_app_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["dry_run_only"] is True
    assert payload["restore_staging_only"] is True
    assert payload["real_orders_enabled"] is False


def test_app_contains_windows_release_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "release_center_snapshot" in text
    assert "launch_release_operation" in text
    assert "def refresh_release_center" in text
    assert "def open_release_center" in text
    assert "Windows Release Center" in text
    assert "Run RC Dry Run" in text
    assert "Create User Backup" in text
    assert "Stage Restore from Backup" in text
    assert "Create Diagnostics Bundle" in text
    assert "Install Desktop Shortcut" in text
