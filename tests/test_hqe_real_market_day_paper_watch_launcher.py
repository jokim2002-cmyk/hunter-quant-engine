from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_guard_check_passes():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "hqe_real_market_day_paper_watch_launcher.py"), "--guard-check"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["guard_check_status"] == "PASS"
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["no_broker_execution"] is True
    assert "place_order" in payload["blocked_order_apis"]


def test_build_payload_waits_when_no_token(tmp_path, monkeypatch):
    monkeypatch.delenv("FYERS_CLIENT_ID", raising=False)
    monkeypatch.delenv("FYERS_ACCESS_TOKEN", raising=False)
    mod = load_module(REPO / "scripts" / "hqe_real_market_day_paper_watch_launcher.py", "m191")
    args = mod.argparse.Namespace(
        workspace=str(tmp_path),
        trading_date="2026-07-10",
        user_id="jokim-local",
        symbol="NSE:NIFTY50-INDEX",
        write=False,
        guard_check=False,
        launch=False,
    )
    payload = mod.build_payload(args)
    assert payload["module_status"] == "PASS"
    assert payload["ready_for_manual_market_watch"] is False
    assert payload["order_api_invoked"] is False
    assert "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd" in payload["watch_launcher_cmd"]


def test_build_payload_ready_when_token_and_data_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "dummy-client")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "dummy-token")
    module_173 = {
        "history_result": {
            "rows": 75,
            "response_redacted": {"s": "ok", "code": 200},
        }
    }
    (tmp_path / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json").write_text(json.dumps(module_173), encoding="utf-8")
    mod = load_module(REPO / "scripts" / "hqe_real_market_day_paper_watch_launcher.py", "m191_ready")
    args = mod.argparse.Namespace(
        workspace=str(tmp_path),
        trading_date="2026-07-10",
        user_id="jokim-local",
        symbol="NSE:NIFTY50-INDEX",
        write=False,
        guard_check=False,
        launch=False,
    )
    payload = mod.build_payload(args)
    assert payload["ready_for_manual_market_watch"] is True
    assert payload["decision"] == "MARKET_DAY_PAPER_WATCH_READY_FOR_MANUAL_START_0915_1530"


def test_cli_write_creates_evidence_and_cmd(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "dummy-client")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "dummy-token")
    module_173 = {
        "history_result": {
            "rows": 75,
            "response_redacted": {"s": "ok", "code": 200},
        }
    }
    (tmp_path / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json").write_text(json.dumps(module_173), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "hqe_real_market_day_paper_watch_launcher.py"),
            "--workspace",
            str(tmp_path),
            "--trading-date",
            "2026-07-10",
            "--user-id",
            "jokim-local",
            "--symbol",
            "NSE:NIFTY50-INDEX",
            "--write",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["module_status"] == "PASS"
    assert (tmp_path / "MODULE_191_REAL_MARKET_DAY_PAPER_WATCH_LAUNCHER_STATUS.json").exists()
    assert (tmp_path / "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd").exists()
    assert (tmp_path / "HQE_MARKET_DAY_PAPER_WATCH_0915_1530.html").exists()
    cmd_text = (tmp_path / "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd").read_text(encoding="utf-8")
    assert "NO ORDERS" in cmd_text
    assert "hqe_real_market_day_paper_watch_launcher.py" in cmd_text
