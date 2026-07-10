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


def test_activation_guard(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = load("hqe_app_v2_license_activation.py", "activation_guard_test")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["machine_bound_license_required"] is True
    assert payload["license_bypass_added"] is False
    assert payload["real_orders_enabled"] is False


def test_blank_key_rejected(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = load("hqe_app_v2_license_activation.py", "activation_blank_test")
    result = module.activate(tmp_path, "")
    assert result["valid"] is False
    assert result["reason"] == "license_key_blank"


def test_app_v2_uses_activation_gui():
    text = (SCRIPTS / "hqe_product_app_v2.py").read_text(encoding="utf-8")
    assert "run_activation_gui" in text
    assert "activation_result = run_activation_gui(" in text


def test_activation_guard_cli():
    cp = subprocess.run(
        [sys.executable, str(SCRIPTS / "hqe_app_v2_license_activation.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(cp.stdout)
    assert payload["guard_check_status"] == "PASS"
    assert payload["license_bypass_added"] is False
