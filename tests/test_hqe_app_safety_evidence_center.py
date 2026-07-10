from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_safety_evidence_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_kill_switch_state_parsing():
    module = load("safety_state")
    assert module.extract_kill_switch_state(
        {"kill_switch": "NO"}
    ) == "CLEAR"
    assert module.extract_kill_switch_state(
        {"kill_switch_triggered": True}
    ) == "TRIGGERED"
    assert module.extract_kill_switch_state(
        {"decision": "KILL SWITCH TRIGGERED"}
    ) == "TRIGGERED"
    assert module.extract_kill_switch_state({}) == "UNKNOWN"


def test_safety_evidence_discovery(tmp_path):
    module = load("safety_discovery")
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "DAY_001_SAFETY_STATUS.json").write_text(
        json.dumps(
            {
                "kill_switch": "NO",
                "guard_check_status": "PASS",
            }
        ),
        encoding="utf-8",
    )
    (workspace / "DAY_001_KILL_SWITCH_EVIDENCE.json").write_text(
        json.dumps({"kill_switch_triggered": False}),
        encoding="utf-8",
    )

    evidence = module.discover_safety_evidence(repo, workspace)
    assert len(evidence) == 2
    assert all(item["kill_switch_state"] == "CLEAR" for item in evidence)
    assert {item["category"] for item in evidence} == {
        "safety",
        "kill_switch",
    }


def test_guard_command_is_guard_check_only(tmp_path):
    module = load("safety_guard_command")
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    venv = repo / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    venv.mkdir(parents=True)
    script = scripts / "example.py"
    script.write_text("print('x')\n", encoding="utf-8")

    # We inspect the helper source to ensure the audit path never contains
    # order or execution flags.
    source = (
        SCRIPTS / "hqe_app_safety_evidence_center.py"
    ).read_text(encoding="utf-8-sig").lower()
    assert "--guard-check" in source
    assert "place_order" not in source
    assert "orderbook" not in source
    assert "tradebook" not in source


def test_guard_keeps_all_execution_locked():
    module = load("safety_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["read_only_evidence_scan"] is True
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_app_contains_safety_evidence_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "safety_snapshot" in text
    assert "launch_safety_audit_worker" in text
    assert "def refresh_safety_evidence_center" in text
    assert "def open_safety_evidence_center" in text
    assert "Safety & Kill-Switch Evidence" in text
    assert "Run Safety Audit" in text
    assert "Open Latest Safety Evidence" in text
