from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_manual_daily_launch_command_pack.py"
spec = importlib.util.spec_from_file_location("hqe_manual_daily_launch_command_pack", MODULE_PATH)
launch_pack = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = launch_pack
spec.loader.exec_module(launch_pack)


def make_repo(tmp_path: Path, missing: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "scripts").mkdir()
    (repo / ".venv" / "Scripts").mkdir(parents=True)
    for _name, rel in launch_pack.REQUIRED_SCRIPTS:
        if rel == missing:
            continue
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# stub\n", encoding="utf-8")
    return repo


def test_launch_pack_passes_with_required_scripts(tmp_path: Path):
    repo = make_repo(tmp_path)
    workspace = tmp_path / "workspace"

    payload = launch_pack.build_launch_pack(repo, workspace, "2026-07-09", 1, write=False)

    assert payload["launch_pack_status"] == "PASS"
    assert payload["decision"] == "SAFE_DAILY_LAUNCH_PACK_READY_MANUAL_LOGIN_REQUIRED"
    assert payload["manual_login_required"] is True
    assert payload["external_api_calls_executed_by_launch_pack"] is False
    assert payload["order_api_invoked_by_launch_pack"] is False
    assert payload["broker_execution_invoked_by_launch_pack"] is False
    assert payload["auto_trading_started_by_launch_pack"] is False
    assert payload["fake_trades_created_by_launch_pack"] is False
    assert payload["real_money_automatic"] is False
    assert payload["no_trade_day_counts_toward_valid_trade_day_target"] is False
    assert payload["script_check"]["all_required_scripts_present"] is True
    assert len(payload["safe_command_sequence"]) >= 6


def test_launch_pack_blocks_missing_required_script(tmp_path: Path):
    missing = "scripts/hqe_fyers_data_only_connector.py"
    repo = make_repo(tmp_path, missing=missing)
    workspace = tmp_path / "workspace"

    payload = launch_pack.build_launch_pack(repo, workspace, "2026-07-09", 1, write=False)

    assert payload["launch_pack_status"] == "BLOCKED"
    assert payload["decision"] == "SAFE_DAILY_LAUNCH_PACK_NOT_READY"
    assert missing in payload["script_check"]["missing_required_scripts"]


def test_write_outputs_creates_evidence_and_launcher(tmp_path: Path):
    repo = make_repo(tmp_path)
    workspace = tmp_path / "workspace"

    payload = launch_pack.build_launch_pack(repo, workspace, "2026-07-09", 1, write=True)

    assert payload["launch_pack_status"] == "PASS"
    assert payload["one_click_launcher_emitted"] is True
    files = payload["evidence_files"]
    assert Path(files["json"]).exists()
    assert Path(files["markdown"]).exists()
    assert Path(files["csv"]).exists()
    assert Path(files["launcher"]).exists()
    loaded = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert loaded["operator_mode"] == "MANUAL_ONE_CLICK_SAFE_LOCAL_RUN"
    launcher_text = Path(files["launcher"]).read_text(encoding="utf-8")
    assert "No real money" in launcher_text
    assert "hqe_final_daily_run_decision_pack.py" in launcher_text


def test_commands_do_not_include_blocked_order_tokens(tmp_path: Path):
    repo = make_repo(tmp_path)
    payload = launch_pack.build_launch_pack(repo, tmp_path / "workspace", "2026-07-09", 1, write=False)

    assert payload["blocked_command_token_hits"] == []
    for command in payload["safe_command_sequence"]:
        assert command["executes_external_api"] is False
        assert command["executes_order_api"] is False
        assert command["starts_auto_trading"] is False


def test_guard_check_is_hard_safe():
    payload = launch_pack.guard_check()

    assert payload["guard_check_status"] == "PASS"
    assert payload["safety_lock"]["paper_only"] is True
    assert payload["safety_lock"]["manual_login_required"] is True
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["no_broker_execution"] is True
    assert payload["order_api_invoked_by_guard_check"] is False
    assert payload["auto_trading_started_by_guard_check"] is False
