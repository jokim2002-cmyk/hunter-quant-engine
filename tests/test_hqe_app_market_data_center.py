from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_market_data_center.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_guard_keeps_all_trading_paths_locked():
    module = load("market_data_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["active_source"] == "fyers"
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_source_registry_keeps_future_brokers_disabled():
    module = load("market_data_sources")
    assert module.SOURCE_REGISTRY["fyers"]["status"] == "AVAILABLE"
    for broker in ("zerodha", "angel_one", "upstox", "groww", "dhan"):
        assert module.SOURCE_REGISTRY[broker]["status"] == "PLACEHOLDER"
        assert module.SOURCE_REGISTRY[broker]["mode"] == "DISABLED"


def test_latest_market_data_reads_csv_and_timestamp(tmp_path):
    module = load("market_data_csv")
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    processed = repo / "data" / "processed"
    processed.mkdir(parents=True)
    workspace.mkdir()
    (processed / "nifty.csv").write_text(
        "datetime,open,high,low,close,volume\n"
        "2026-07-10T09:15:00+05:30,1,2,0,1.5,100\n"
        "2026-07-10T09:20:00+05:30,1,2,0,1.5,120\n",
        encoding="utf-8",
    )
    payload = module.latest_market_data(repo, workspace)
    assert payload["rows"] == 2
    assert payload["path"].endswith("nifty.csv")
    assert payload["latest_timestamp_utc"]
    assert payload["status"] in {
        "LIVE", "STALE", "CHECK", "MARKET_CLOSED_EVIDENCE",
    }


def test_safe_refresh_command_is_data_only(tmp_path):
    module = load("market_data_command")
    command = module.safe_refresh_command(
        tmp_path, tmp_path / "workspace", "NSE:NIFTY50-INDEX"
    )
    joined = " ".join(command).lower()
    assert "--execute-live-data-only" in joined
    assert "place_order" not in joined
    assert "orderbook" not in joined
    assert "tradebook" not in joined


def test_app_contains_unified_market_data_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "market_data_snapshot" in text
    assert "launch_market_data_worker" in text
    assert "def refresh_market_data_center" in text
    assert "def open_market_data_center" in text
    assert "Unified Market Data Center" in text
    assert "Refresh Fyers Data Now" in text
    assert "Open Latest Data File" in text
