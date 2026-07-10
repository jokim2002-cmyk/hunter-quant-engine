from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_broker_data_health.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_guard_keeps_all_execution_locked():
    module = load("broker_health_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_snapshot_detects_credentials_without_exposing_values(tmp_path):
    module = load("broker_health_snapshot")
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    secrets = repo / "secrets"
    secrets.mkdir(parents=True)
    workspace.mkdir()
    (secrets / "fyers_client_id.txt").write_text("CLIENT-123", encoding="utf-8")
    (secrets / "fyers_access_token.txt").write_text(
        "super-secret-token", encoding="utf-8"
    )
    (workspace / "MODULE_173_FYERS_FETCHER_STATUS.json").write_text(
        json.dumps({"status": "PASS", "rows": 75}),
        encoding="utf-8",
    )

    payload = module.broker_health_snapshot(
        repo, workspace, check_internet=False
    )
    rendered = json.dumps(payload)
    assert payload["broker_status"] == "READY_FOR_DATA_TEST"
    assert payload["market_data"]["status"] == "LIVE"
    assert "super-secret-token" not in rendered
    assert payload["secret_values_redacted"] is True
    assert payload["real_orders_enabled"] is False


def test_safe_test_blocks_when_login_missing(monkeypatch, tmp_path):
    module = load("broker_health_block")
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    empty_auth = tmp_path / "empty_auth"
    repo.mkdir()
    workspace.mkdir()
    empty_auth.mkdir()

    monkeypatch.delenv("FYERS_CLIENT_ID", raising=False)
    monkeypatch.delenv("FYERS_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(module, "local_auth_root", lambda: empty_auth)

    payload = module.execute_safe_data_test(
        repo, workspace, "NSE:NIFTY50-INDEX"
    )
    assert payload["status"] == "BLOCKED"
    assert payload["real_orders_enabled"] is False
    assert (workspace / module.STATUS_FILE).exists()


def test_safe_command_is_data_only(tmp_path):
    module = load("broker_health_command")
    command = module.safe_test_command(
        tmp_path, tmp_path / "workspace", "NSE:NIFTY50-INDEX"
    )
    joined = " ".join(command).lower()
    assert "--execute-live-data-only" in joined
    assert "place_order" not in joined
    assert "tradebook" not in joined
    assert "orderbook" not in joined


def test_app_has_embedded_broker_data_health_controls():
    text = APP.read_text(encoding="utf-8-sig")
    assert "broker_health_snapshot" in text
    assert "launch_broker_health_worker" in text
    assert "def refresh_broker_data_health" in text
    assert "def run_safe_broker_data_test" in text
    assert 'text="Refresh Broker/Data Health"' in text
    assert 'text="Run Safe Data Test"' in text
