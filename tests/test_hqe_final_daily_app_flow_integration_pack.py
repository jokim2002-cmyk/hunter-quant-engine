from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_final_daily_app_flow_integration_pack.py"
spec = importlib.util.spec_from_file_location("hqe_final_daily_app_flow_integration_pack", MODULE_PATH)
flow = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = flow
spec.loader.exec_module(flow)


def test_plan_reports_required_flow_steps_and_safety_lock(tmp_path):
    payload = flow.build_flow_plan(
        repo_root=Path(__file__).resolve().parents[1],
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
        execute_approved_local_steps=False,
    )
    step_ids = {step["step_id"] for step in payload["planned_steps"]}
    assert "01_LOGIN_STATUS_GATE" in step_ids
    assert "02_MARKET_SESSION_SUPERVISOR" in step_ids
    assert "03_FYERS_DATA_ONLY_PREFLIGHT" in step_ids
    assert "04_PAPER_SIGNAL_NO_TRADE_REASON" in step_ids
    assert "06_DAY_LEDGER_EVALUATOR" in step_ids
    assert "07_30_VALID_TRADE_DAY_TRACKER" in step_ids
    assert payload["safety_lock"]["paper_only"] is True
    assert payload["safety_lock"]["no_real_money"] is True
    assert payload["safety_lock"]["no_broker_execution"] is True
    assert payload["real_money_automatic"] is False


def test_default_plan_does_not_execute_or_start_trading(tmp_path):
    payload = flow.build_flow_plan(
        repo_root=Path(__file__).resolve().parents[1],
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
        execute_approved_local_steps=False,
    )
    assert payload["execute_approved_local_steps_requested"] is False
    assert payload["external_api_calls_executed_by_integration_pack"] is False
    assert payload["order_api_invoked_by_integration_pack"] is False
    assert payload["broker_execution_invoked_by_integration_pack"] is False
    assert payload["auto_trading_started_by_integration_pack"] is False
    assert payload["fake_trades_created_by_integration_pack"] is False
    assert all(step["execution_approved_for_this_run"] is False for step in payload["planned_steps"])


def test_write_outputs_creates_json_markdown_and_ledger(tmp_path):
    payload = flow.build_flow_plan(
        repo_root=Path(__file__).resolve().parents[1],
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
        execute_approved_local_steps=False,
    )
    files = flow.write_outputs(tmp_path, payload)
    assert Path(files["json"]).exists()
    assert Path(files["markdown"]).exists()
    assert Path(files["ledger"]).exists()
    loaded = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert loaded["version"] == flow.VERSION
    assert "PC_ON" in loaded["daily_flow"]


def test_guard_check_hard_blocks_dangerous_capabilities():
    guard = flow.guard_check()
    assert guard["guard_check_status"] == "PASS"
    assert guard["blocked_capabilities"]["place_order"] == "HARD_BLOCKED"
    assert guard["blocked_capabilities"]["auto_trading"] == "HARD_BLOCKED"
    assert guard["startup_order_api"] is False
    assert guard["real_money_automatic"] is False


def test_missing_required_script_fails_in_empty_repo(tmp_path):
    empty_repo = tmp_path / "repo"
    empty_repo.mkdir()
    payload = flow.build_flow_plan(
        repo_root=empty_repo,
        workspace=tmp_path / "workspace",
        trading_date="2026-07-09",
        day_number=1,
        execute_approved_local_steps=False,
    )
    assert payload["integration_status"] == "FAIL_MISSING_REQUIRED_FLOW_STEPS"
    assert "01_LOGIN_STATUS_GATE" in payload["missing_required_steps"]
    assert "FINAL_DAILY_APP_FLOW_NOT_READY_FIX_MISSING_STEPS" == payload["decision"]
