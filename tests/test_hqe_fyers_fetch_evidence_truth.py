from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_fyers_fetch_evidence_truth.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_fyers_truth_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_candle(workspace: Path, candle: datetime) -> None:
    path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    path.write_text(
        "datetime,open,high,low,close,volume\n"
        f"{candle.isoformat()},1,1,1,1,1\n",
        encoding="utf-8",
    )


def write_fetch_status(workspace: Path, status: str) -> None:
    path = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    path.write_text(json.dumps({"status": status}), encoding="utf-8")


def process_fixture():
    return [
        {"ProcessId": 100, "ParentProcessId": 50, "ExecutablePath": "venv-python.exe", "CommandLine": "watch"},
        {"ProcessId": 101, "ParentProcessId": 100, "ExecutablePath": "python.exe", "CommandLine": "watch"},
    ]


def test_parse_iso_datetime():
    module = load_module()
    value = module.parse_datetime("2026-07-10T10:30:00+05:30")
    assert value == datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)


def test_canonical_pid_uses_root_process():
    module = load_module()
    payload = module.canonical_watch_process(process_fixture())
    assert payload["canonical_pid"] == 100
    assert payload["process_count"] == 2
    assert payload["canonical_reason"] == "ROOT_WATCH_PROCESS"


def test_truth_detects_fresh_live_data(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    write_candle(tmp_path, now - timedelta(minutes=5))
    write_fetch_status(tmp_path, "DATA_ONLY_HISTORY_CALL_COMPLETED")

    payload = module.build_truth(tmp_path, now=now, processes=process_fixture())

    assert payload["fetch_truth"] == "LIVE_DATA_FRESH"
    assert payload["operator_recommendation"] == "CONTINUE_PAPER_WATCH"
    assert payload["canonical_watch_pid"] == 100
    assert payload["real_orders_enabled"] is False


def test_truth_detects_completed_but_stale(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    write_candle(tmp_path, now - timedelta(minutes=30))
    write_fetch_status(tmp_path, "DATA_ONLY_HISTORY_CALL_COMPLETED")

    payload = module.build_truth(tmp_path, now=now, processes=process_fixture())

    assert payload["fetch_truth"] == "FETCH_COMPLETED_BUT_CANDLE_STALE"
    assert payload["operator_recommendation"] == "RESTART_WATCH_ONLY_AFTER_FETCH_DIAGNOSTIC"


def test_truth_detects_fetch_failure(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    write_candle(tmp_path, now - timedelta(minutes=5))
    write_fetch_status(tmp_path, "FAIL")

    payload = module.build_truth(tmp_path, now=now, processes=process_fixture())

    assert payload["fetch_truth"] == "FETCH_FAILED"
