from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_watch_health_monitor.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_watch_health_monitor_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_data_file(workspace: Path, modified: datetime) -> None:
    path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    path.write_text("datetime,close\nx,1\n", encoding="utf-8")
    timestamp = modified.timestamp()
    path.touch()
    import os
    os.utime(path, (timestamp, timestamp))


def test_health_is_healthy_for_recent_data(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    write_data_file(tmp_path, now - timedelta(seconds=60))

    payload = module.collect_health(
        tmp_path,
        now=now,
        process_override={"running": True, "pid": 123, "reason": "PROCESS_FOUND"},
        write=False,
    )

    assert payload["overall_health"] == "HEALTHY"
    assert payload["consecutive_stale_cycles"] == 0
    assert payload["real_orders_enabled"] is False


def test_health_is_degraded_for_stale_data(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)
    write_data_file(tmp_path, now - timedelta(minutes=20))

    payload = module.collect_health(
        tmp_path,
        now=now,
        process_override={"running": True, "pid": 456, "reason": "PROCESS_FOUND"},
        write=True,
    )

    assert payload["overall_health"] == "DEGRADED_DATA_STALE"
    assert payload["consecutive_stale_cycles"] == 1

    payload2 = module.collect_health(
        tmp_path,
        now=now + timedelta(seconds=5),
        process_override={"running": True, "pid": 456, "reason": "PROCESS_FOUND"},
        write=True,
    )
    assert payload2["consecutive_stale_cycles"] == 2


def test_health_is_stopped_when_process_missing(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 10, 5, 0, tzinfo=timezone.utc)

    payload = module.collect_health(
        tmp_path,
        now=now,
        process_override={"running": False, "pid": None, "reason": "PROCESS_NOT_FOUND"},
        write=False,
    )

    assert payload["overall_health"] == "STOPPED"
    assert payload["process_running"] is False


def test_market_closed_is_idle_not_degraded(tmp_path):
    module = load_module()
    now = datetime(2026, 7, 11, 5, 0, tzinfo=timezone.utc)

    payload = module.collect_health(
        tmp_path,
        now=now,
        process_override={"running": True, "pid": 789, "reason": "PROCESS_FOUND"},
        write=False,
    )

    assert payload["overall_health"] == "MARKET_CLOSED_IDLE"
    assert payload["consecutive_stale_cycles"] == 0
