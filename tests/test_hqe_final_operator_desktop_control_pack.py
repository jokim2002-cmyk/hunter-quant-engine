import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_final_operator_desktop_control_pack.py"
spec = importlib.util.spec_from_file_location("hqe_final_operator_desktop_control_pack", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def create_required_scripts(repo_root: Path):
    for _key, relative_text in module.REQUIRED_OPERATOR_SCRIPTS:
        path = repo_root / module.as_repo_relative(relative_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# stub\n", encoding="utf-8")


def test_guard_check_blocks_order_and_trading_tokens():
    payload = module.guard_check()
    assert payload["guard_check_status"] == "PASS"
    assert payload["forbidden_command_guard_violations"] == []
    assert payload["order_api_invoked_by_guard_check"] is False
    assert payload["broker_execution_invoked_by_guard_check"] is False
    assert payload["auto_trading_started_by_guard_check"] is False
    assert payload["fake_trades_created_by_guard_check"] is False
    assert payload["real_money_automatic"] is False


def test_build_control_pack_ready_when_scripts_present(tmp_path):
    create_required_scripts(tmp_path)
    workspace = tmp_path / "workspace"
    payload = module.build_control_pack(tmp_path, workspace, "2026-07-09", 1)
    assert payload["control_pack_status"] == "PASS"
    assert payload["decision"] == "FINAL_OPERATOR_DESKTOP_CONTROL_PACK_READY_MANUAL_REVIEW_REQUIRED"
    assert payload["missing_required_scripts"] == []
    assert payload["manual_login_required"] is True
    assert payload["external_api_calls_executed_by_control_pack"] is False
    assert payload["order_api_invoked_by_control_pack"] is False
    assert payload["broker_execution_invoked_by_control_pack"] is False
    assert payload["auto_trading_started_by_control_pack"] is False
    assert payload["fake_trades_created_by_control_pack"] is False


def test_missing_scripts_are_reported_without_creating_fake_readiness(tmp_path):
    workspace = tmp_path / "workspace"
    payload = module.build_control_pack(tmp_path, workspace, "2026-07-09", 1)
    assert payload["control_pack_status"] == "PASS"
    assert payload["decision"] == "FINAL_OPERATOR_DESKTOP_CONTROL_PACK_READY_WITH_MISSING_LOCAL_SCRIPTS"
    assert payload["missing_required_scripts"]
    assert payload["real_money_automatic"] is False


def test_write_control_pack_outputs(tmp_path):
    create_required_scripts(tmp_path)
    workspace = tmp_path / "workspace"
    payload = module.build_control_pack(tmp_path, workspace, "2026-07-09", 1)
    evidence = module.write_control_pack_outputs(payload, workspace)
    assert Path(evidence["json"]).exists()
    assert Path(evidence["markdown"]).exists()
    assert Path(evidence["commands_csv"]).exists()
    assert Path(evidence["safe_cmd_launcher"]).exists()
    loaded = json.loads(Path(evidence["json"]).read_text(encoding="utf-8"))
    assert loaded["operator_mode"] == "FINAL_DESKTOP_CONTROL_PANEL_LOCAL_ONLY"
    assert "NO ORDERS" in Path(evidence["safe_cmd_launcher"]).read_text(encoding="utf-8")


def test_operator_commands_are_manual_and_safe(tmp_path):
    commands = module.build_safe_operator_commands(tmp_path / "workspace", "2026-07-09", 1)
    assert len(commands) >= 5
    for item in commands:
        assert ".venv" in item["command"]
        assert not module.command_contains_forbidden_token(item["command"])
    joined = "\n".join(item["command"] for item in commands).lower()
    assert "--write" in joined
    assert "place_order" not in joined
