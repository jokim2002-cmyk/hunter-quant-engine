from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_market_session_supervisor.py"
spec = importlib.util.spec_from_file_location("hqe_market_session_supervisor", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_pre_market_wait_phase(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T09:00:00")
    assert payload["supervisor_status"] == "PASS"
    assert payload["decision"] == "PRE_MARKET_WAIT"
    assert payload["watch_window_active"] is False
    assert payload["should_watch_market"] is False
    assert payload["external_api_calls_executed"] is False


def test_market_watch_active_phase_at_start(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T09:15:00")
    assert payload["decision"] == "MARKET_WATCH_ACTIVE"
    assert payload["watch_window_active"] is True
    assert payload["should_watch_market"] is True
    assert "paper_only_signal_evaluation" in payload["allowed_local_actions"]


def test_market_watch_active_phase_at_end_inclusive(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T15:30:00")
    assert payload["decision"] == "MARKET_WATCH_ACTIVE"
    assert payload["watch_window_active"] is True


def test_post_market_report_due_phase(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T15:31:00")
    assert payload["decision"] == "POST_MARKET_REPORT_DUE"
    assert payload["should_generate_daily_report"] is True
    assert payload["order_api_invoked"] is False


def test_weekend_closed_phase(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-11T10:00:00")
    assert payload["decision"] == "MARKET_CLOSED_NON_TRADING_DAY"
    assert payload["should_generate_closed_day_status"] is True
    assert payload["should_watch_market"] is False


def test_utc_timestamp_converts_to_ist(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T03:45:00Z")
    assert payload["now_ist"].startswith("2026-07-09T09:15:00")
    assert payload["decision"] == "MARKET_WATCH_ACTIVE"


def test_write_evidence_files_and_ledger(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T15:31:00", write=True)
    paths = payload["evidence_files"]
    json_path = Path(paths["json"])
    md_path = Path(paths["markdown"])
    ledger_path = Path(paths["ledger"])

    assert json_path.exists()
    assert md_path.exists()
    assert ledger_path.exists()
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["decision"] == "POST_MARKET_REPORT_DUE"

    with ledger_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["decision"] == "POST_MARKET_REPORT_DUE"
    assert rows[0]["external_api_calls_executed"] == "False"


def test_safety_lock_and_blocked_actions_are_strict(tmp_path: Path):
    payload = module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T10:00:00")
    safety = payload["safety_lock"]
    assert safety["paper_only"] is True
    assert safety["no_real_orders"] is True
    assert safety["no_auto_trading"] is True
    assert safety["no_fake_trades"] is True
    assert safety["no_candidate_tuning_during_validation"] is True
    assert "place_order" in payload["blocked_actions"]
    assert payload["actual_trade_rows_created"] == 0


def test_guard_check_blocks_order_and_external_actions():
    guard = module.build_guard_check()
    assert guard["guard_check_status"] == "PASS"
    assert guard["blocked_actions"]["place_order"].startswith("ACTION_BLOCKED")
    assert guard["blocked_actions"]["external_api_call_from_supervisor"].startswith("ACTION_BLOCKED")
    assert guard["external_api_calls_executed"] is False
    assert guard["order_api_invoked"] is False


def test_invalid_session_window_rejected(tmp_path: Path):
    try:
        module.run_supervisor(workspace=tmp_path, now_value="2026-07-09T10:00:00", session_start="15:30", session_end="09:15")
    except ValueError as exc:
        assert "market_session_start" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("invalid session window should fail")

