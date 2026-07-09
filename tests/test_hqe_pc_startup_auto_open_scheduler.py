from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "hqe_pc_startup_auto_open_scheduler.py"
spec = importlib.util.spec_from_file_location("hqe_pc_startup_auto_open_scheduler", MODULE_PATH)
scheduler = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scheduler
spec.loader.exec_module(scheduler)


def test_plan_is_login_gate_only(tmp_path):
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()
    payload = scheduler.run_scheduler_plan(workspace=str(workspace), repo=str(repo), write=False)

    assert payload["scheduler_status"] == "PASS"
    assert payload["scheduler_mode"] == "LOCAL_STARTUP_LOGIN_GATE_ONLY"
    assert payload["startup_trigger"] == "WINDOWS_ONLOGON"
    assert payload["startup_action"] == "OPEN_LOCAL_HQE_LOGIN_STATUS_GATE_ONLY"
    assert payload["requires_operator_login"] is True
    assert payload["requires_manual_operator_control"] is True
    assert payload["auto_start_trading"] is False
    assert payload["auto_broker_connect"] is False
    assert payload["auto_order_execution"] is False
    assert payload["external_api_calls_executed"] is False
    assert payload["order_api_invoked"] is False
    assert payload["broker_execution_invoked"] is False
    assert payload["plaintext_secrets_written"] is False
    assert payload["warnings"] == []


def test_write_creates_status_launcher_and_manual_task_commands(tmp_path):
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()

    payload = scheduler.run_scheduler_plan(workspace=str(workspace), repo=str(repo), write=True)
    evidence = payload["evidence_files"]

    assert Path(evidence["json"]).exists()
    assert Path(evidence["markdown"]).exists()
    assert Path(evidence["ledger"]).exists()
    assert Path(evidence["launcher"]).exists()
    assert Path(evidence["task_commands"]).exists()

    stored = json.loads(Path(evidence["json"]).read_text(encoding="utf-8"))
    assert stored["decision"] == "STARTUP_LOGIN_GATE_PLAN_READY_MANUAL_INSTALL_REQUIRED"
    assert stored["scheduled_task_installed_by_this_run"] is False

    launcher_text = Path(evidence["launcher"]).read_text(encoding="utf-8")
    assert "hqe_local_login_shell.py" in launcher_text
    assert "--status" in launcher_text
    assert "no real money" in launcher_text.lower()
    assert "no auto trading" in launcher_text.lower()


def test_guard_check_hard_blocks_startup_trading_paths():
    payload = scheduler.guard_check_payload()

    assert payload["guard_check_status"] == "PASS"
    assert payload["auto_start_trading"] is False
    assert payload["auto_broker_connect"] is False
    assert payload["auto_order_execution"] is False
    assert payload["external_api_calls_executed"] is False
    assert payload["order_api_invoked"] is False
    assert payload["broker_execution_invoked"] is False
    assert payload["plaintext_secrets_written"] is False
    assert payload["blocked_startup_actions"]["place_order"] == "HARD_BLOCKED"
    assert payload["blocked_startup_actions"]["auto_trade"] == "HARD_BLOCKED"
    assert payload["safety_lock"]["paper_only"] is True
    assert payload["safety_lock"]["requires_operator_login"] is True


def test_task_commands_are_manual_not_executed(tmp_path):
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()

    commands = scheduler.build_task_commands(repo, workspace)

    assert "manual operator use only" in commands.lower()
    assert "schtasks /Create" in commands
    assert "schtasks /Delete" in commands
    assert "broker execution" in commands.lower()
    assert "auto trading" in commands.lower()
    assert "FYERS_ACCESS_TOKEN" not in commands
    assert "FYERS_CLIENT_ID" not in commands


def test_validate_plan_blocks_forbidden_flags(tmp_path):
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()
    plan = scheduler.build_plan(repo, workspace)
    plan["auto_start_trading"] = True

    warnings = scheduler.validate_plan(plan)

    assert "FORBIDDEN_STARTUP_FLAG_TRUE:auto_start_trading" in warnings
