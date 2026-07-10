from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manual_smoke_pass_written(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = load("hqe_app_v2_manual_smoke_result.py", "manual_smoke_test")
    payload = module.build_payload(tmp_path, "PASS", "visual smoke passed")
    module.write_outputs(tmp_path, payload)

    assert payload["manual_smoke_pass"] is True
    assert payload["real_orders_enabled"] is False
    assert (tmp_path / "HQE_APP_V2_MANUAL_SMOKE_RESULT.json").exists()


def test_manual_smoke_fail_returns_nonzero(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_manual_smoke_result.py"),
            "--workspace",
            str(tmp_path),
            "--result",
            "FAIL",
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    assert payload["manual_smoke_pass"] is False


def test_release_freeze_waits_without_evidence(tmp_path):
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_app_v2_release_freeze.py"),
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    assert payload["release_freeze_status"] == "HOLD"
    assert payload["real_orders_enabled"] is False
