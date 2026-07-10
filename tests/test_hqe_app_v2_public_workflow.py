from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def test_public_workflow_guard(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_public_workflow.py"),
            "--workspace",
            str(tmp_path),
            "--guard-check",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    assert payload["guard_check_status"] == "PASS"
    assert payload["visible_powershell_required"] is False
    assert payload["visible_cmd_required_after_launch"] is False
    assert payload["real_orders_enabled"] is False


def test_launcher_written(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_public_workflow.py"),
            "--workspace",
            str(tmp_path),
            "--write-launcher",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    launcher = REPO / "OPEN_HQE_APP_V2.cmd"
    assert payload["launcher_exists"] is True
    assert launcher.exists()
    text = launcher.read_text(encoding="utf-8").lower()
    assert "hqe_product_app_v2.py" in text
    assert "place_order" not in text


def test_final_dry_run(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_final_dry_run.py"),
            "--workspace",
            str(tmp_path),
            "--write",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    assert payload["dry_run_status"] == "PASS"
    assert payload["checks"]["six_brokers_present"] is True
    assert payload["checks"]["real_orders_locked"] is True
    assert (tmp_path / "HQE_APP_V2_FINAL_DRY_RUN.json").exists()
    assert (tmp_path / "HQE_APP_V2_FINAL_DRY_RUN.html").exists()
