from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_market_data_provider_registry.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_symbol_mapping_across_providers():
    module = load("provider_symbols")
    assert module.provider_symbol("fyers", "NIFTY") == "NSE:NIFTY50-INDEX"
    assert module.provider_symbol("zerodha", "NIFTY50") == "NSE:NIFTY 50"
    assert module.provider_symbol("upstox", "BANKNIFTY") == (
        "NSE_INDEX|Nifty Bank"
    )


def test_non_fyers_providers_remain_disabled_placeholders(tmp_path):
    module = load("provider_placeholders")
    registry = module.provider_registry_snapshot(tmp_path)
    by_name = {
        item["provider"]: item
        for item in registry["providers"]
    }
    for name in ("zerodha", "angel_one", "upstox", "groww", "dhan"):
        assert by_name[name]["effective_status"] == "DISABLED_PLACEHOLDER"
        assert by_name[name]["execution"] is False


def test_fyers_command_is_data_only(tmp_path):
    module = load("provider_fyers_command")
    repo = tmp_path / "repo"
    script = repo / "scripts" / "hqe_fyers_historical_5m_data_only_fetcher.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('x')\n", encoding="utf-8")
    command = module.safe_fyers_fetch_command(
        repo,
        tmp_path / "workspace",
        "NIFTY",
        help_text=(
            "--workspace --symbol --execute-live-data-only --write"
        ),
    )
    joined = " ".join(command).lower()
    assert "--execute-live-data-only" in joined
    assert "place_order" not in joined
    assert "orderbook" not in joined
    assert "tradebook" not in joined


def test_registry_guard_locks_execution():
    module = load("provider_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["other_providers_disabled"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
