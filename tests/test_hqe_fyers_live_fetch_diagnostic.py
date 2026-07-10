from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_fyers_live_fetch_diagnostic.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location("hqe_fyers_live_fetch_diagnostic_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_detect_live_flag():
    module = load_module()
    assert module.detect_live_flag("--execute-live-data-only") == "--execute-live-data-only"
    assert module.detect_live_flag("--help only") is None


def test_build_command_applies_live_flag(tmp_path):
    module = load_module()
    payload = module.build_command(
        Path("python.exe"),
        Path("fetcher.py"),
        tmp_path,
        "--workspace --symbol --user-id --write --execute-live-data-only",
        True,
    )

    assert payload["live_flag"] == "--execute-live-data-only"
    assert payload["live_flag_applied"] is True
    assert "--execute-live-data-only" in payload["command"]


def test_offline_sample_classification():
    module = load_module()
    execution = {
        "executed": True,
        "live_flag_applied": False,
        "timed_out": False,
        "returncode": 0,
        "before": {"sample_csv": {"sha256": "a", "row_count": 1, "latest_candle_utc": "x"}},
        "after": {"sample_csv": {"sha256": "a", "row_count": 1, "latest_candle_utc": "x"}},
    }
    status = {
        "external_api_calls_executed": False,
        "history_result": {
            "executed": False,
            "rows": 0,
            "status": "OFFLINE_SAMPLE_SCHEMA_BY_DEFAULT",
        },
    }

    payload = module.classify(execution, status)
    assert payload["decision"] == "LIVE_FETCH_NOT_REQUESTED_OFFLINE_SAMPLE_ONLY"


def test_api_not_executed_classification():
    module = load_module()
    execution = {
        "executed": True,
        "live_flag_applied": True,
        "timed_out": False,
        "returncode": 0,
        "before": {"sample_csv": {"sha256": "a", "row_count": 1, "latest_candle_utc": "x"}},
        "after": {"sample_csv": {"sha256": "a", "row_count": 1, "latest_candle_utc": "x"}},
    }
    status = {
        "external_api_calls_executed": False,
        "history_result": {"executed": False, "rows": 0, "status": "READY"},
    }

    payload = module.classify(execution, status)
    assert payload["decision"] == "LIVE_FETCH_FLAG_APPLIED_BUT_API_NOT_EXECUTED"


def test_same_content_rewrite_is_not_update():
    module = load_module()
    execution = {
        "executed": True,
        "live_flag_applied": True,
        "timed_out": False,
        "returncode": 0,
        "before": {"sample_csv": {"sha256": "same", "row_count": 5, "latest_candle_utc": "x"}},
        "after": {"sample_csv": {"sha256": "same", "row_count": 5, "latest_candle_utc": "x"}},
    }
    status = {
        "external_api_calls_executed": True,
        "history_result": {"executed": True, "rows": 5, "status": "PASS"},
    }

    payload = module.classify(execution, status)
    assert payload["decision"] == "LIVE_FETCH_REPORTED_SUCCESS_BUT_CSV_CONTENT_UNCHANGED"
