from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_operator_dashboard.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_trade_log(path: Path, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["trade_id", "status"])
        for index in range(rows):
            writer.writerow([index + 1, "PAPER"])


def test_validation_progress_counts_days_trades_and_weeks(tmp_path):
    module = load("operator_progress")
    log_one = tmp_path / "DAY_001_FORWARD_TRADE_LOG.csv"
    log_two = tmp_path / "DAY_002_FORWARD_TRADE_LOG.csv"
    write_trade_log(log_one, 2)
    write_trade_log(log_two, 3)

    sessions = [
        {
            "trading_date": "2026-07-10",
            "artifacts": [
                {
                    "category": "trade_log",
                    "path": str(log_one),
                }
            ],
        },
        {
            "trading_date": "2026-07-13",
            "artifacts": [
                {
                    "category": "trade_log",
                    "path": str(log_two),
                }
            ],
        },
        {
            "trading_date": "2026-07-14",
            "artifacts": [],
        },
    ]
    progress = module.validation_progress_from_sessions(sessions)
    assert progress["observed_days"] == 3
    assert progress["observed_trades"] == 5
    assert progress["valid_trade_days"] == 2
    assert progress["no_trade_days"] == 1
    assert progress["expiry_weeks"] == 2
    assert progress["validation_minimums_complete"] is False


def test_next_action_prioritizes_safety():
    module = load("operator_next_action_safety")
    action = module.choose_next_action(
        auth={"status": "READY"},
        market_data={"latest_data": {"rows": 100}},
        startup={"overall_status": "READY"},
        paper_watch={"running": False},
        daily_close={"overall_status": "CHECK_REQUIRED"},
        safety={"overall_status": "ATTENTION_REQUIRED"},
    )
    assert action["code"] == "REVIEW_SAFETY"


def test_next_action_connect_then_watch():
    module = load("operator_next_action_flow")
    connect = module.choose_next_action(
        auth={"status": "CHECK"},
        market_data={"latest_data": {"rows": 100}},
        startup={"overall_status": "READY"},
        paper_watch={"running": False},
        daily_close={"overall_status": "CHECK_REQUIRED"},
        safety={"overall_status": "LOCKED_SAFE"},
    )
    assert connect["code"] == "CONNECT_BROKER"

    watch = module.choose_next_action(
        auth={"status": "READY"},
        market_data={"latest_data": {"rows": 100}},
        startup={"overall_status": "READY"},
        paper_watch={"running": False},
        daily_close={"overall_status": "CHECK_REQUIRED"},
        safety={"overall_status": "LOCKED_SAFE"},
    )
    assert watch["code"] == "START_WATCH"


def test_guard_keeps_all_execution_locked():
    module = load("operator_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["read_only_aggregation"] is True
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_app_contains_consolidated_operator_dashboard():
    text = APP.read_text(encoding="utf-8-sig")
    assert "operator_dashboard_snapshot" in text
    assert "def refresh_operator_dashboard" in text
    assert "def open_operator_dashboard" in text
    assert "Operator Dashboard" in text
    assert "Connect → Prepare → Watch → Close → Review" in text
    assert "Validation Progress" in text
    assert "Open Next Recommended Action" in text
