from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_daily_operations.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_latest_day_and_idempotent_next_day(tmp_path):
    module = load("daily_ops_day_test")
    day = tmp_path / "DAY_001_MARKET_CLOSE_PACK"
    day.mkdir()
    (day / "DAY_001_MARKET_CLOSE_EVIDENCE.json").write_text(
        json.dumps({"day_number": 1, "trading_date": "2026-07-10"}), encoding="utf-8"
    )
    (tmp_path / "MODULE_200_NEXT_MARKET_DAY_STARTUP_PACK_STATUS.json").write_text(
        json.dumps({"day_number": 2, "trading_date": "2026-07-13"}), encoding="utf-8"
    )
    latest = module.resolve_latest_validation_day(tmp_path)
    assert latest["day_number"] == 1
    assert module.resolve_next_day(tmp_path) == (2, "2026-07-13")
    assert module.resolve_next_day(tmp_path) == (2, "2026-07-13")


def test_weekend_skip():
    module = load("daily_ops_weekend_test")
    assert module.next_market_date("2026-07-10") == "2026-07-13"


def test_dynamic_report_and_evidence(tmp_path):
    module = load("daily_ops_report_test")
    day = tmp_path / "DAY_002_MARKET_CLOSE_PACK"
    day.mkdir()
    report = day / "DAY_002_DAILY_CLOSE_REPORT.html"
    evidence = day / "DAY_002_MARKET_CLOSE_EVIDENCE.json"
    report.write_text("report", encoding="utf-8")
    evidence.write_text(json.dumps({"day_number": 2, "trading_date": "2026-07-13"}), encoding="utf-8")
    assert module.resolve_latest_report(tmp_path) == report
    assert module.resolve_latest_evidence(tmp_path) == evidence


def test_guard_and_action_are_separate(tmp_path):
    module = load("daily_ops_command_test")
    repo = tmp_path / "repo"
    (repo / ".venv" / "Scripts").mkdir(parents=True)
    (repo / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    guard = module.build_guard_command(repo, "sample.py")
    action = module.build_action_command(repo, tmp_path, "sample.py", "2026-07-10", 1, "jokim-local", "NSE:NIFTY50-INDEX")
    assert "--guard-check" in guard and "--write" not in guard
    assert "--write" in action and "--guard-check" not in action


def test_safety_snapshot(tmp_path):
    module = load("daily_ops_safety_test")
    payload = module.operations_snapshot(tmp_path)
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["fake_trades_allowed"] is False
    assert payload["safety_lock"]["no_candidate_tuning_during_validation"] is True


def test_app_batch2_controls_and_no_hardcoded_day1():
    text = APP.read_text(encoding="utf-8-sig")
    for label in (
        "Prepare Next Market Day", "Run Day Rollover Guard",
        "Generate Daily Close Report", "Refresh Latest Report",
        "Open Latest Evidence", "Embedded Live Status",
    ):
        assert f'text="{label}"' in text
    assert "launch_operation_worker(" in text
    assert "operations_snapshot(workspace)" in text
    assert "resolve_latest_report(workspace)" in text
    assert "resolve_latest_evidence(workspace)" in text
    assert "DAY_001_MARKET_CLOSE_PACK" not in text
    assert "DAY_001_MARKET_CLOSE_EVIDENCE.json" not in text
    assert "DAY_001_MARKET_CLOSE_EVIDENCE.html" not in text
    assert 'text="Place Order"' not in text
