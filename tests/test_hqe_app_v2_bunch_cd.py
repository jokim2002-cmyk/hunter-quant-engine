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


def test_broker_center_guard(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = load("hqe_broker_connect_center.py", "broker_center_test")
    payload = module.guard_payload()
    assert payload["broker_count"] == 6
    assert payload["credential_persistence"] == "DISABLED"
    assert payload["real_orders_enabled"] is False


def test_broker_readiness_redacts_secret(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = load("hqe_broker_connect_center.py", "broker_readiness_test")
    payload = module.readiness_payload(
        "fyers", {"client_id": "abc", "access_token": "secret-token"})
    assert "secret-token" not in json.dumps(payload)
    assert payload["credential_values_written_to_disk"] is False


def test_hidden_supervisor_guard(tmp_path):
    cp = subprocess.run(
        [sys.executable, str(SCRIPTS / "hqe_hidden_paper_watch_supervisor.py"),
         "--workspace", str(tmp_path), "--guard-check"],
        capture_output=True, text=True, check=True)
    payload = json.loads(cp.stdout)
    assert payload["guard_check_status"] == "PASS"
    assert payload["visible_terminal_required"] is False
    assert payload["real_orders_enabled"] is False


def test_hidden_supervisor_status(tmp_path):
    cp = subprocess.run(
        [sys.executable, str(SCRIPTS / "hqe_hidden_paper_watch_supervisor.py"),
         "--workspace", str(tmp_path), "--status"],
        capture_output=True, text=True, check=True)
    payload = json.loads(cp.stdout)
    assert payload["status"] == "NOT_RUNNING"
    assert payload["process_alive"] is False


def test_app_v2_broker_center_button():
    text = (SCRIPTS / "hqe_product_app_v2.py").read_text(encoding="utf-8")
    assert "def open_broker_connect_center()" in text
    assert 'text="Broker Connect Center"' in text


def test_integration_evidence(tmp_path):
    cp = subprocess.run(
        [sys.executable, str(SCRIPTS / "hqe_app_v2_integration_evidence.py"),
         "--workspace", str(tmp_path), "--write"],
        capture_output=True, text=True, check=True)
    payload = json.loads(cp.stdout)
    assert payload["integration_status"] == "PASS"
    assert payload["real_orders_enabled"] is False
    assert (tmp_path / "HQE_APP_V2_INTEGRATION_EVIDENCE.json").exists()
    assert (tmp_path / "HQE_APP_V2_INTEGRATION_EVIDENCE.html").exists()
