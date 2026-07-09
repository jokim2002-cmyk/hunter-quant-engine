from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "hqe_30_day_paper_validation_daily_operating_sop.py"
spec = importlib.util.spec_from_file_location("hqe_30_day_paper_validation_daily_operating_sop", SCRIPT_PATH)
sop = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sop
spec.loader.exec_module(sop)


def _write_day_ledger(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["trading_date", "day_number", "trade_count", "day_status"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_no_trade_day_counts_observed_not_valid(tmp_path):
    workspace = tmp_path / "workspace"
    _write_day_ledger(
        workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        [{"trading_date": "2026-07-09", "day_number": "1", "trade_count": "0", "day_status": "ZERO_TRADE_DAY_RECORDED"}],
    )

    payload = sop.build_sop_payload(workspace=workspace, trading_date="2026-07-09", day_number=1, repo_root=tmp_path)

    assert payload["sop_status"] == "PASS"
    assert payload["observed_session_days"] == 1
    assert payload["valid_paper_trade_days"] == 0
    assert payload["no_trade_observed_days"] == 1
    assert payload["remaining_valid_trade_days"] == 30
    assert payload["daily_operating_rules"]["no_trade_day_counts_as_valid_trade_day"] is False
    assert payload["real_money_policy"]["real_money_automatic_after_target"] is False


def test_valid_trade_day_requires_trade_count_gt_zero(tmp_path):
    workspace = tmp_path / "workspace"
    _write_day_ledger(
        workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        [
            {"trading_date": "2026-07-09", "day_number": "1", "trade_count": "0", "day_status": "ZERO_TRADE_DAY_RECORDED"},
            {"trading_date": "2026-07-10", "day_number": "2", "trade_count": "2", "day_status": "TRADE_DAY_RECORDED"},
        ],
    )

    payload = sop.build_sop_payload(workspace=workspace, repo_root=tmp_path)

    assert payload["observed_session_days"] == 2
    assert payload["valid_paper_trade_days"] == 1
    assert payload["no_trade_observed_days"] == 1
    assert payload["remaining_valid_trade_days"] == 29
    details = payload["day_ledger_summary"]["day_details"]
    assert details[0]["counts_as_valid_paper_trade_day"] is False
    assert details[1]["counts_as_valid_paper_trade_day"] is True


def test_bom_header_is_normalized(tmp_path):
    workspace = tmp_path / "workspace"
    ledger = workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    workspace.mkdir(parents=True, exist_ok=True)
    ledger.write_text("\ufeffdate,day_number,trade_count\n2026-07-09,1,0\n", encoding="utf-8")

    payload = sop.build_sop_payload(workspace=workspace, repo_root=tmp_path)

    assert payload["day_ledger_summary"]["day_ledger_rows"] == 1
    assert payload["observed_session_days"] == 1
    assert payload["valid_paper_trade_days"] == 0


def test_write_outputs_creates_sop_files_without_execution(tmp_path):
    workspace = tmp_path / "workspace"
    payload = sop.build_sop_payload(workspace=workspace, repo_root=tmp_path)
    evidence = sop.write_sop_outputs(workspace, payload)

    assert Path(evidence["json"]).exists()
    assert Path(evidence["markdown"]).exists()
    assert Path(evidence["cmd"]).exists()
    assert "No broker, no orders, no auto trading" in Path(evidence["cmd"]).read_text(encoding="utf-8")
    loaded = json.loads(Path(evidence["json"]).read_text(encoding="utf-8"))
    assert loaded["external_api_calls_executed_by_sop"] is False
    assert loaded["order_api_invoked_by_sop"] is False
    assert loaded["fake_trades_created_by_sop"] is False


def test_guard_check_hard_blocks_real_money_and_execution():
    payload = sop.guard_check_payload()

    assert payload["guard_check_status"] == "PASS"
    assert payload["safety_lock"]["paper_only"] is True
    assert payload["safety_lock"]["no_real_money"] is True
    assert payload["safety_lock"]["no_broker_execution"] is True
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["no_auto_trading"] is True
    assert payload["safety_lock"]["no_option_selling"] is True
    assert payload["external_api_calls_executed_by_sop"] is False
    assert payload["broker_execution_invoked_by_sop"] is False
    assert payload["auto_trading_started_by_sop"] is False
    assert payload["real_money_automatic"] is False
