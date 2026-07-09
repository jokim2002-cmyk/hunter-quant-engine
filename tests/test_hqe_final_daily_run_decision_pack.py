from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_final_daily_run_decision_pack.py"
spec = importlib.util.spec_from_file_location("hqe_final_daily_run_decision_pack", MODULE_PATH)
pack = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pack
assert spec.loader is not None
spec.loader.exec_module(pack)


def make_required_scripts(root: Path) -> None:
    for candidates in pack.REQUIRED_SCRIPT_CANDIDATES.values():
        rel = candidates[0]
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# test stub\n", encoding="utf-8")


def test_guard_check_never_invokes_trading_or_api() -> None:
    payload = pack.run_guard_check()
    assert payload["guard_check_status"] == "PASS"
    assert payload["external_api_calls_executed_by_decision_pack"] is False
    assert payload["order_api_invoked_by_decision_pack"] is False
    assert payload["broker_execution_invoked_by_decision_pack"] is False
    assert payload["auto_trading_started_by_decision_pack"] is False
    assert payload["fake_trades_created_by_decision_pack"] is False
    assert payload["real_money_automatic"] is False
    assert payload["blocked_actions"]["place_order"] == "HARD_BLOCKED"


def test_missing_scripts_block_decision(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    cfg = pack.DecisionPackConfig(repo_root=tmp_path / "repo", workspace=workspace)
    payload = pack.build_decision_pack(cfg)
    assert payload["decision_pack_status"] == "FAIL"
    assert payload["decision"] == "FINAL_DAILY_RUN_BLOCKED_MISSING_REQUIRED_SCRIPTS"
    assert payload["manual_operator_launch_ready"] is False


def test_all_scripts_but_no_login_requires_manual_login(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()
    workspace.mkdir()
    make_required_scripts(repo)
    cfg = pack.DecisionPackConfig(repo_root=repo, workspace=workspace, trading_date="2026-07-09", day_number=1)
    payload = pack.build_decision_pack(cfg)
    assert payload["decision_pack_status"] == "PASS"
    assert payload["decision"] == "FINAL_DAILY_RUN_READY_MANUAL_LOGIN_REQUIRED"
    assert payload["manual_operator_launch_ready"] is False
    assert payload["login_state"]["manual_login_required_before_daily_run"] is True


def test_authenticated_session_allows_manual_operator_launch_ready(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()
    workspace.mkdir()
    make_required_scripts(repo)
    (workspace / pack.DEFAULT_SESSION_FILE_NAME).write_text(
        json.dumps({"authenticated": True, "session_status": "SESSION_ACTIVE"}),
        encoding="utf-8",
    )
    cfg = pack.DecisionPackConfig(repo_root=repo, workspace=workspace)
    payload = pack.build_decision_pack(cfg)
    assert payload["decision_pack_status"] == "PASS"
    assert payload["decision"] == "FINAL_DAILY_RUN_READY_AFTER_MANUAL_LOGIN"
    assert payload["manual_operator_launch_ready"] is True
    assert payload["login_state"]["manual_login_required_before_daily_run"] is False


def test_write_outputs_creates_json_markdown_and_ledger(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    repo.mkdir()
    workspace.mkdir()
    make_required_scripts(repo)
    cfg = pack.DecisionPackConfig(repo_root=repo, workspace=workspace, trading_date="2026-07-09", day_number=1)
    payload = pack.build_decision_pack(cfg)
    files = pack.write_outputs(workspace, payload)
    assert Path(files["json"]).exists()
    assert Path(files["markdown"]).exists()
    assert Path(files["ledger"]).exists()
    saved = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert saved["version"] == pack.VERSION
    assert "no_real_money" in Path(files["markdown"]).read_text(encoding="utf-8")
    assert "decision" in Path(files["ledger"]).read_text(encoding="utf-8")
