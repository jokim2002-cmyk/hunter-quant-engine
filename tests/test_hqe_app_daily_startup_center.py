from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_daily_startup_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_next_market_day_skips_weekend():
    module = load("startup_date")
    assert module.next_market_day(date(2026, 7, 10)).isoformat() == "2026-07-13"


def test_dynamic_day_discovery(tmp_path):
    module = load("startup_days")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "DAY_001_FORWARD_TRADE_LOG.csv").write_text("x\n", encoding="utf-8")
    (workspace / "DAY_014_MARKET_CLOSE_EVIDENCE.json").write_text("{}", encoding="utf-8")
    assert module.discover_day_numbers(workspace) == [1, 14]
    assert module.latest_day_number(workspace) == 14


def test_prepare_command_is_data_only(tmp_path):
    module = load("startup_command")
    command = module.prepare_next_day_command(
        tmp_path,
        tmp_path / "workspace",
        trading_date="2026-07-13",
        day_number=2,
    )
    joined = " ".join(command).lower()
    assert "--write" in joined
    assert "--day-number 2" in joined
    assert "place_order" not in joined
    assert "tradebook" not in joined
    assert "orderbook" not in joined


def test_guard_keeps_all_trading_locked():
    module = load("startup_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_app_contains_daily_startup_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "daily_readiness_snapshot" in text
    assert "launch_daily_startup_worker" in text
    assert "operation_status" in text
    assert "def refresh_daily_startup_center" in text
    assert "def open_daily_startup_center" in text
    assert "Daily Startup & Checklist" in text
    assert "Run Daily Readiness" in text
    assert "Prepare Next Market Day" in text
