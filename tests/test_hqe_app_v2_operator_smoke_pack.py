from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def test_ui_readiness_gate(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_ui_readiness_gate.py"),
            "--workspace",
            str(tmp_path),
            "--write",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    assert payload["ui_readiness_status"] == "PASS"
    assert payload["checks"]["real_order_controls_absent"] is True
    assert payload["real_orders_enabled"] is False
    assert (tmp_path / "HQE_APP_V2_UI_READINESS_GATE.json").exists()


def test_operator_smoke_pack_written(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_operator_smoke_pack.py"),
            "--workspace",
            str(tmp_path),
            "--write",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    assert payload["operator_smoke_status"] == "READY_FOR_MANUAL_REVIEW"
    assert payload["required_check_count"] == 10
    assert payload["real_orders_enabled"] is False
    assert (tmp_path / "HQE_APP_V2_OPERATOR_SMOKE_PACK.json").exists()
    assert (tmp_path / "HQE_APP_V2_OPERATOR_SMOKE_CHECKLIST.md").exists()
    assert (tmp_path / "RUN_HQE_APP_V2_OPERATOR_SMOKE.cmd").exists()


def test_operator_smoke_has_no_order_action():
    text = (SCRIPTS / "hqe_app_v2_operator_smoke_pack.py").read_text(encoding="utf-8")
    assert "Place Order" not in text
    assert "NO_ORDER_CONTROLS" in text
