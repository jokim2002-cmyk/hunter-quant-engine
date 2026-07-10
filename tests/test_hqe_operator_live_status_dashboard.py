from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_operator_live_status_dashboard.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location("hqe_operator_dashboard_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_freshness_labels(monkeypatch):
    module = load_module()
    fixed = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(module, "utc_now", lambda: fixed)

    assert module.freshness_label(fixed - timedelta(seconds=30)) == "FRESH"
    assert module.freshness_label(fixed - timedelta(minutes=5)) == "RECENT"
    assert module.freshness_label(fixed - timedelta(minutes=30)) == "STALE"
    assert module.freshness_label(None) == "UNKNOWN"


def test_format_ist():
    module = load_module()
    value = datetime(2026, 7, 10, 4, 48, 34, tzinfo=timezone.utc)

    assert module.format_ist(value) == "10-07-2026 10:18:34 AM IST"
    assert module.format_ist(None) == "UNKNOWN"


def test_derive_status_reads_workspace(tmp_path):
    module = load_module()

    (tmp_path / "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json").write_text(
        json.dumps(
            {
                "status": "RUNNING",
                "symbol": "NSE:NIFTY50-INDEX",
                "generated_at_utc": "2026-07-10T05:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json").write_text(
        json.dumps(
            {
                "broker": "Fyers",
                "generated_at_utc": "2026-07-10T05:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    evidence = tmp_path / "HQE_APP_V2_CONTROLLED_DRY_RUNS_20260710_100000"
    evidence.mkdir()
    (evidence / "HQE_APP_V2_CONTROLLED_DRY_RUN_SUMMARY.json").write_text(
        json.dumps(
            {
                "decision": "APP_V2_CONTROLLED_DRY_RUNS_COMPLETE",
            }
        ),
        encoding="utf-8",
    )

    payload = module.derive_status(tmp_path)

    assert payload["watch_status"] == "RUNNING"
    assert payload["broker"] == "Fyers"
    assert payload["symbol"] == "NSE:NIFTY50-INDEX"
    assert payload["latest_update_ist"] == "10-07-2026 10:30:00 AM IST"
    assert payload["latest_decision"] == "APP_V2_CONTROLLED_DRY_RUNS_COMPLETE"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False


def test_missing_workspace_files_stays_safe(tmp_path):
    module = load_module()
    payload = module.derive_status(tmp_path)

    assert payload["data_freshness"] == "UNKNOWN"
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False

def test_market_session_open():
    module = load_module()
    now = datetime(2026, 7, 10, 10, 0, tzinfo=module.INDIA_TZ)
    payload = module.market_session(now)
    assert payload["status"] == "OPEN"
    assert "Market closes in" in payload["next_event"]


def test_market_session_preopen():
    module = load_module()
    now = datetime(2026, 7, 10, 8, 0, tzinfo=module.INDIA_TZ)
    payload = module.market_session(now)
    assert payload["status"] == "PRE-OPEN"
    assert "Market opens in" in payload["next_event"]


def test_data_age_text(monkeypatch):
    module = load_module()
    fixed = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(module, "utc_now", lambda: fixed)
    value = fixed - timedelta(minutes=3, seconds=5)
    assert module.data_age_text(value) == "3m 5s"
    assert module.data_age_text(None) == "UNKNOWN"

def test_dashboard_health_payload(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.setattr(
        module,
        "collect_health",
        lambda workspace, write=True: {
            "overall_health": "DEGRADED_DATA_STALE",
            "heartbeat_ist": "10-07-2026 11:00:00 AM IST",
            "last_successful_data_update_ist": "10-07-2026 10:30:00 AM IST",
            "consecutive_stale_cycles": 3,
            "fetch_failure_reason": "NONE_REPORTED",
        },
    )

    payload = module.derive_status(tmp_path)

    assert payload["system_health"] == "DEGRADED_DATA_STALE"
    assert payload["consecutive_stale_cycles"] == 3
    assert payload["real_orders_enabled"] is False

def test_dashboard_fetch_truth_payload(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.setattr(
        module,
        "collect_health",
        lambda workspace, write=True: {
            "overall_health": "DEGRADED_DATA_STALE",
            "heartbeat_ist": "10-07-2026 11:00:00 AM IST",
            "last_successful_data_update_ist": "10-07-2026 10:30:00 AM IST",
            "consecutive_stale_cycles": 3,
            "fetch_failure_reason": "NONE_REPORTED",
        },
    )
    monkeypatch.setattr(
        module,
        "build_truth",
        lambda workspace: {
            "fetch_truth": "FETCH_COMPLETED_BUT_CANDLE_STALE",
            "latest_candle_ist": "10-07-2026 10:20:00 AM IST",
            "latest_candle_age_minutes": 40.0,
            "canonical_watch_pid": 100,
            "watch_process_count": 2,
            "operator_recommendation": "RESTART_WATCH_ONLY_AFTER_FETCH_DIAGNOSTIC",
        },
    )

    payload = module.derive_status(tmp_path)

    assert payload["fetch_truth"] == "FETCH_COMPLETED_BUT_CANDLE_STALE"
    assert payload["canonical_watch_pid"] == 100
    assert payload["watch_process_count"] == 2
    assert payload["real_orders_enabled"] is False
