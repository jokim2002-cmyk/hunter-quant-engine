from pathlib import Path
import csv
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hqe_final_paper_validation_master_handoff_freeze_pack.py"
spec = importlib.util.spec_from_file_location("hqe_final_paper_validation_master_handoff_freeze_pack", SCRIPT)
freeze_pack = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = freeze_pack
spec.loader.exec_module(freeze_pack)


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def prepare_repo_root(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for rel in freeze_pack.REQUIRED_REPO_FILES:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# placeholder\n", encoding="utf-8")
    return repo


def test_day001_freeze_counts_observed_not_valid(tmp_path):
    workspace = tmp_path / "workspace"
    repo = prepare_repo_root(tmp_path)
    write_csv(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv", [
        {
            "trading_date": "2026-07-09",
            "day_number": "1",
            "day_status": "ZERO_TRADE_DAY_RECORDED",
            "trade_count": "0",
            "safety_ok": "YES",
        }
    ])

    payload = freeze_pack.build_payload(workspace=workspace, repo_root=repo)

    assert payload["freeze_pack_status"] == "PASS"
    assert payload["observed_session_days"] == 1
    assert payload["valid_paper_trade_days"] == 0
    assert payload["no_trade_observed_days"] == 1
    assert payload["remaining_valid_trade_days"] == 30
    assert payload["actual_paper_trades"] == 0
    assert payload["distinct_expiry_weeks"] == 0
    assert payload["decision"] == "PAPER_VALIDATION_FREEZE_READY_HOLD_MORE_VALID_TRADE_DAYS_REQUIRED"
    assert payload["real_money_automatic"] is False
    assert payload["safety_lock"]["no_fake_trades"] is True


def test_valid_trade_days_only_when_trade_count_positive(tmp_path):
    workspace = tmp_path / "workspace"
    repo = prepare_repo_root(tmp_path)
    write_csv(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv", [
        {"trading_date": "2026-07-09", "trade_count": "0", "safety_ok": "YES"},
        {"trading_date": "2026-07-10", "trade_count": "2", "safety_ok": "YES"},
        {"trading_date": "2026-07-11", "trade_count": "1", "safety_ok": "YES"},
    ])
    write_csv(workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv", [
        {"trading_date": "2026-07-10", "expiry": "2026-07-16", "net": "100"},
        {"trading_date": "2026-07-10", "expiry": "2026-07-16", "net": "-50"},
        {"trading_date": "2026-07-11", "expiry": "2026-07-23", "net": "25"},
    ])

    payload = freeze_pack.build_payload(workspace=workspace, repo_root=repo)

    assert payload["observed_session_days"] == 3
    assert payload["valid_paper_trade_days"] == 2
    assert payload["no_trade_observed_days"] == 1
    assert payload["actual_paper_trades"] == 3
    assert payload["distinct_expiry_weeks"] == 2
    assert payload["cumulative_forward_net"] == 75.0


def test_missing_required_repo_file_fails_freeze(tmp_path):
    workspace = tmp_path / "workspace"
    repo = prepare_repo_root(tmp_path)
    missing_file = repo / freeze_pack.REQUIRED_REPO_FILES[0]
    missing_file.unlink()
    write_csv(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv", [
        {"trading_date": "2026-07-09", "trade_count": "0", "safety_ok": "YES"}
    ])

    payload = freeze_pack.build_payload(workspace=workspace, repo_root=repo)

    assert payload["freeze_pack_status"] == "FAIL"
    assert payload["decision"] == "FREEZE_PACK_REPO_INCOMPLETE_FIX_REQUIRED"
    assert freeze_pack.REQUIRED_REPO_FILES[0] in payload["repo_checks"]["missing_required_repo_files"]


def test_write_outputs_creates_json_markdown_ledger_and_launcher(tmp_path):
    workspace = tmp_path / "workspace"
    repo = prepare_repo_root(tmp_path)
    write_csv(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv", [
        {"trading_date": "2026-07-09", "trade_count": "0", "safety_ok": "YES"}
    ])
    payload = freeze_pack.build_payload(workspace=workspace, repo_root=repo)
    files = freeze_pack.write_outputs(payload, workspace)

    for path_text in files.values():
        assert Path(path_text).exists()

    saved = json.loads(Path(files["json"]).read_text(encoding="utf-8"))
    assert saved["version"] == freeze_pack.VERSION
    md = Path(files["markdown"]).read_text(encoding="utf-8")
    assert "Real-money rule" in md
    assert "No-trade day rule" in md


def test_guard_check_is_hard_locked():
    guard = freeze_pack.guard_check_payload()

    assert guard["guard_check_status"] == "PASS"
    assert guard["external_api_calls_executed_by_freeze_pack"] is False
    assert guard["order_api_invoked_by_freeze_pack"] is False
    assert guard["broker_execution_invoked_by_freeze_pack"] is False
    assert guard["auto_trading_started_by_freeze_pack"] is False
    assert guard["fake_trades_created_by_freeze_pack"] is False
    assert guard["real_money_automatic"] is False
    assert guard["safety_lock"]["real_money_manual_review_only"] is True
