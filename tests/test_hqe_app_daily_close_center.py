from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_daily_close_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dynamic_day_and_date_discovery(tmp_path):
    module = load("daily_close_discovery")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "DAY_003_FORWARD_TRADE_LOG_2026-07-14.csv").write_text(
        "x\n",
        encoding="utf-8",
    )
    (workspace / "DAY_012_MARKET_CLOSE_EVIDENCE_20260723.json").write_text(
        "{}",
        encoding="utf-8",
    )
    assert module.latest_day_number(workspace) == 12
    assert module.discover_latest_trading_date(workspace) == "2026-07-23"


def test_close_command_is_report_only(tmp_path):
    module = load("daily_close_command_test")
    command = module.daily_close_command(
        tmp_path,
        tmp_path / "workspace",
        trading_date="2026-07-23",
        day_number=12,
    )
    joined = " ".join(command).lower()
    assert "--write" in joined
    assert "--day-number 12" in joined
    assert "place_order" not in joined
    assert "orderbook" not in joined
    assert "tradebook" not in joined


def test_guard_keeps_all_trading_locked():
    module = load("daily_close_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_app_contains_daily_close_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "daily_close_snapshot" in text
    assert "launch_daily_close_worker" in text
    assert "def refresh_daily_close_center" in text
    assert "def open_daily_close_center" in text
    assert "Daily Close & Report" in text
    assert "Generate Daily Close Report" in text
    assert "Open Trader Report" in text
    assert "Open Technical Evidence (JSON)" in text
