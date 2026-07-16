from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load_module(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(
        module_name,
        SCRIPTS / filename,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_six_broker_registry_is_data_only():
    module = load_module(
        "hqe_multi_broker_data_architecture.py",
        "hqe_multi_broker_test",
    )

    assert list(module.BROKER_REGISTRY) == [
        "fyers",
        "zerodha",
        "angel_one",
        "upstox",
        "groww",
        "dhan",
    ]

    for definition in module.BROKER_REGISTRY.values():
        assert definition.execution_enabled is False
        assert definition.order_methods_available is False


def test_adapter_contract_has_no_order_methods():
    module = load_module(
        "hqe_multi_broker_data_architecture.py",
        "hqe_multi_broker_contract_test",
    )

    public_methods = {
        name
        for name in dir(module.DataOnlyBrokerAdapter)
        if not name.startswith("_")
    }

    assert public_methods == {
        "connection_test",
        "credential_status",
        "market_data_status",
    }

    assert not public_methods.intersection(module.BLOCKED_ORDER_ACTIONS)


def test_multi_broker_guard_check(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_multi_broker_data_architecture.py"),
            "--workspace",
            str(tmp_path),
            "--guard-check",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    assert payload["guard_check_status"] == "PASS"
    assert payload["broker_count"] == 6
    assert payload["forbidden_order_methods_found"] == []
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False


def test_architecture_status_written(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_multi_broker_data_architecture.py"),
            "--workspace",
            str(tmp_path),
            "--status",
            "--write",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    output = tmp_path / "HQE_MULTI_BROKER_DATA_ARCHITECTURE_STATUS.json"

    assert payload["architecture_status"] == "PASS"
    assert payload["broker_count"] == 6
    assert output.exists()

    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["real_money_enabled"] is False
    assert stored["real_orders_enabled"] is False


def test_app_v2_guard_check():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_product_app_v2.py"),
            "--guard-check",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    assert payload["guard_check_status"] == "PASS"
    assert payload["hidden_background_runner_supported"] is True
    assert payload["visible_cmd_required_for_daily_use"] is False
    assert payload["no_real_orders"] is True
    assert payload["no_broker_execution"] is True
    assert payload["no_auto_trading"] is True


def test_app_v2_status_is_safe(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "hqe_product_app_v2.py"),
            "--workspace",
            str(tmp_path),
            "--status",
            "--write-status",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)

    assert payload["broker_count"] == 6
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert (
        tmp_path / "HQE_APP_V2_PUBLIC_TRADER_UI_STATUS.json"
    ).exists()


def test_hidden_controller_command_is_paper_watch_only(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = load_module(
        "hqe_product_app_v2.py",
        "hqe_product_app_v2_controller_test",
    )

    captured = {}

    class FakeProcess:
        pid = 12345

        def poll(self):
            return None

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(
        module,
        "find_existing_paper_watch_processes",
        lambda: [],
    )
    monkeypatch.setattr(
        module,
        "paper_product_status",
        lambda workspace: {"running": False},
    )
    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)

    controller = module.HiddenPaperWatchController(
        workspace=tmp_path,
        user_id="test-user",
        symbol="NSE:NIFTY50-INDEX",
    )

    result = controller.start()
    command_text = " ".join(captured["command"]).lower()

    assert result["status"] == "RUNNING_CANONICAL_PAPER_RUNTIME"
    assert "hqe_paper_product_runtime.py" in command_text
    assert "hqe_market_day_persistent_paper_watch_loop.py" not in command_text
    assert "--run-data-fetch" in command_text
    assert "place_order" not in command_text
    assert result["broker_execution_invoked"] is False
    assert result["order_api_invoked"] is False
