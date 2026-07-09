from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hqe_final_safe_daily_run_smoke_pack.py"
spec = importlib.util.spec_from_file_location("hqe_final_safe_daily_run_smoke_pack", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = smoke
assert spec.loader is not None
spec.loader.exec_module(smoke)


def write_day_ledger(workspace: Path, rows: list[dict[str, str]]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["trading_date", "day_number", "trade_count", "safety_ok"])
        writer.writeheader()
        writer.writerows(rows)


def create_required_repo_files(repo_root: Path) -> None:
    for relative in smoke.REQUIRED_REPO_SCRIPTS:
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# placeholder\n", encoding="utf-8")


def test_guard_check_hard_blocks_trading_and_api() -> None:
    payload = smoke.guard_check()
    assert payload["guard_check_status"] == "PASS"
    assert payload["external_api_calls_executed_by_smoke_pack"] is False
    assert payload["order_api_invoked_by_smoke_pack"] is False
    assert payload["broker_execution_invoked_by_smoke_pack"] is False
    assert payload["auto_trading_started_by_smoke_pack"] is False
    assert payload["fake_trades_created_by_smoke_pack"] is False
    assert payload["real_money_automatic"] is False
    assert payload["blocked_actions"]["place_order"] == "HARD_BLOCKED_BY_SMOKE_PACK"


def test_smoke_pack_passes_with_required_scripts_and_day_ledger(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    create_required_repo_files(repo_root)
    write_day_ledger(workspace, [{"trading_date": "2026-07-09", "day_number": "1", "trade_count": "0", "safety_ok": "YES"}])

    payload = smoke.build_smoke_pack(workspace=workspace, repo_root=repo_root, trading_date="2026-07-09", day_number=1)

    assert payload["smoke_pack_status"] == "PASS"
    assert payload["decision"] == "FINAL_SAFE_DAILY_RUN_SMOKE_PASS_MANUAL_OPERATOR_REVIEW_REQUIRED"
    assert payload["observed_session_days"] == 1
    assert payload["valid_paper_trade_days"] == 0
    assert payload["no_trade_observed_days"] == 1
    assert payload["required_ok"] is True
    assert payload["safety_ok"] is True
    assert payload["external_api_calls_executed_by_smoke_pack"] is False
    assert payload["order_api_invoked_by_smoke_pack"] is False


def test_smoke_pack_fails_when_required_script_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    create_required_repo_files(repo_root)
    (repo_root / smoke.REQUIRED_REPO_SCRIPTS[0]).unlink()
    write_day_ledger(workspace, [{"trading_date": "2026-07-09", "day_number": "1", "trade_count": "0", "safety_ok": "YES"}])

    payload = smoke.build_smoke_pack(workspace=workspace, repo_root=repo_root)

    assert payload["smoke_pack_status"] == "FAIL"
    assert smoke.REQUIRED_REPO_SCRIPTS[0] in payload["missing_required_repo_scripts"]
    assert payload["decision"] == "FINAL_SAFE_DAILY_RUN_SMOKE_FAIL_FIX_REQUIRED_ITEMS"


def test_smoke_pack_fails_when_day_ledger_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    create_required_repo_files(repo_root)

    payload = smoke.build_smoke_pack(workspace=workspace, repo_root=repo_root)

    assert payload["smoke_pack_status"] == "FAIL"
    assert "FORWARD_VALIDATION_DAY_LEDGER.csv" in payload["missing_required_workspace_files"]


def test_write_evidence_creates_json_markdown_and_ledger(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    create_required_repo_files(repo_root)
    write_day_ledger(workspace, [{"trading_date": "2026-07-09", "day_number": "1", "trade_count": "0", "safety_ok": "YES"}])

    payload = smoke.build_smoke_pack(workspace=workspace, repo_root=repo_root, trading_date="2026-07-09", day_number=1, write=True)

    files = payload["evidence_files"]
    assert Path(files["json"]).exists()
    assert Path(files["markdown"]).exists()
    assert Path(files["ledger"]).exists()
    saved = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert saved["smoke_pack_status"] == "PASS"
    assert saved["real_money_automatic"] is False

