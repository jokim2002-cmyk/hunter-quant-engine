from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_session_history_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dynamic_session_grouping_and_categories(tmp_path):
    module = load("session_history_grouping")
    workspace = tmp_path / "workspace"
    day_one = workspace / "DAY_001_2026-07-10"
    day_two = workspace / "archive" / "DAY_002_20260713"
    day_one.mkdir(parents=True)
    day_two.mkdir(parents=True)

    (day_one / "DAY_001_FORWARD_TRADE_LOG.csv").write_text(
        "x\n",
        encoding="utf-8",
    )
    (day_one / "DAY_001_MARKET_CLOSE_EVIDENCE.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (day_two / "DAY_002_DAILY_REPORT.txt").write_text(
        "report",
        encoding="utf-8",
    )

    sessions = module.discover_session_history(workspace)
    assert [session["day_number"] for session in sessions] == [2, 1]
    assert sessions[0]["trading_date"] == "2026-07-13"
    assert sessions[0]["category_counts"]["report"] == 1
    assert sessions[1]["category_counts"]["trade_log"] == 1
    assert sessions[1]["category_counts"]["evidence"] == 1


def test_search_filters_days_and_artifacts(tmp_path):
    module = load("session_history_filter")
    sessions = [
        {
            "day_number": 2,
            "day_label": "DAY_002",
            "trading_date": "2026-07-13",
            "artifacts": [
                {
                    "name": "DAY_002_DAILY_REPORT.txt",
                    "category": "report",
                    "path": "x",
                }
            ],
        },
        {
            "day_number": 1,
            "day_label": "DAY_001",
            "trading_date": "2026-07-10",
            "artifacts": [
                {
                    "name": "DAY_001_FORWARD_TRADE_LOG.csv",
                    "category": "trade_log",
                    "path": "y",
                }
            ],
        },
    ]

    assert len(module.filter_sessions(sessions, "report")) == 1
    assert module.filter_sessions(sessions, "2026-07-10")[0]["day_number"] == 1
    assert len(module.filter_sessions(sessions, "")) == 2


def test_guard_is_read_only_and_trading_locked():
    module = load("session_history_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["read_only_browser"] is True
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_app_contains_session_history_browser():
    text = APP.read_text(encoding="utf-8-sig")
    assert "session_history_snapshot" in text
    assert "filter_sessions" in text
    assert "def refresh_session_history_center" in text
    assert "def open_session_history_center" in text
    assert "Session History & Evidence" in text
    assert "Open Selected Artifact" in text
    assert "Open Day Folder" in text
    assert "Search Sessions" in text
