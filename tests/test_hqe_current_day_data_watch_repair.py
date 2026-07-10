from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_current_day_data_watch_repair.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location("hqe_current_day_repair_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_status(workspace: Path, code: int = 200, status: str = "ok"):
    path = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    path.write_text(
        json.dumps(
            {
                "history_result": {
                    "rows": 1,
                    "response_redacted": {
                        "code": code,
                        "s": status,
                        "message": "",
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def write_csv(workspace: Path, stamp: str):
    path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("datetime", "open", "high", "low", "close", "volume", "source"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "datetime": stamp,
                "open": 1,
                "high": 1,
                "low": 1,
                "close": 1,
                "volume": 1,
                "source": "fyers_history_api",
            }
        )


def test_canonical_process_root():
    module = load_module()
    payload = module.canonical_process(
        [
            {"ProcessId": 10, "ParentProcessId": 1},
            {"ProcessId": 11, "ParentProcessId": 10},
        ]
    )
    assert payload["canonical_pid"] == 10
    assert payload["process_count"] == 2


def test_unified_health_healthy(monkeypatch, tmp_path):
    module = load_module()
    current = datetime(2026, 7, 10, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    monkeypatch.setattr(module, "now_ist", lambda: current)
    monkeypatch.setattr(
        module,
        "canonical_process",
        lambda processes=None: {
            "running": True,
            "canonical_pid": 100,
            "process_count": 1,
            "reason": "ROOT_PYTHON_WATCH_PROCESS",
        },
    )
    write_status(tmp_path)
    write_csv(tmp_path, "2026-07-10T11:55:00+05:30")

    payload = module.derive_unified_health(tmp_path)

    assert payload["overall_health"] == "HEALTHY"
    assert payload["current_day_candle_present"] is True
    assert payload["canonical_pid"] == 100


def test_unified_health_current_day_missing(monkeypatch, tmp_path):
    module = load_module()
    current = datetime(2026, 7, 10, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    monkeypatch.setattr(module, "now_ist", lambda: current)
    monkeypatch.setattr(
        module,
        "canonical_process",
        lambda processes=None: {
            "running": True,
            "canonical_pid": 100,
            "process_count": 1,
            "reason": "ROOT_PYTHON_WATCH_PROCESS",
        },
    )
    write_status(tmp_path)
    write_csv(tmp_path, "2026-07-09T15:25:00+05:30")

    payload = module.derive_unified_health(tmp_path)

    assert payload["overall_health"] == "CURRENT_DAY_DATA_MISSING"
