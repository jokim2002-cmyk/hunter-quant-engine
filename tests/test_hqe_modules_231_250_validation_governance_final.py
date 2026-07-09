from __future__ import annotations

import csv
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


def test_common_safety_lock():
    common = load_module(REPO / "scripts" / "hqe_modules_231_250_common.py", "hqe_modules_231_250_common")
    assert common.SAFETY_LOCK["paper_only"] is True
    assert common.SAFETY_LOCK["no_real_orders"] is True
    assert common.SAFETY_LOCK["no_broker_execution"] is True
    assert common.SAFETY_LOCK["no_auto_trading"] is True
    assert len(common.MODULES) == 20


def test_all_module_guard_checks():
    common = load_module(REPO / "scripts" / "hqe_modules_231_250_common.py", "hqe_modules_231_250_common_guard")
    for number, meta in common.MODULES.items():
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts" / meta["file"]), "--guard-check"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        assert payload["guard_check_status"] == "PASS"
        assert payload["module_number"] == number
        assert payload["safety_lock"]["no_real_orders"] is True


def test_runner_creates_master_dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "dummy-client")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "dummy-token")
    with (tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["trading_date", "day_number", "trade_count"])
        writer.writeheader()
        writer.writerow({"trading_date": "2026-07-10", "day_number": "1", "trade_count": "0"})

    (tmp_path / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv").write_text(
        "datetime,open,high,low,close,volume,symbol,source\n2026-07-10T09:15:00+05:30,1,2,1,2,100,NSE:NIFTY50-INDEX,test\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO / "scripts" / "RUN_MODULES_231_250_VALIDATION_GOVERNANCE_FINAL.ps1"),
            "-Workspace", str(tmp_path),
            "-TradingDate", "2026-07-10",
            "-DayNumber", "1",
            "-UserId", "jokim-local",
            "-Symbol", "NSE:NIFTY50-INDEX",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "MODULES_231_250_VALIDATION_GOVERNANCE_FINAL_SAFE_RUN_COMPLETE" in result.stdout
    final_json = tmp_path / "MODULE_250_MASTER_SYSTEM_STATUS_DASHBOARD_STATUS.json"
    assert final_json.exists()
    payload = json.loads(final_json.read_text(encoding="utf-8"))
    assert payload["modules_231_to_250_complete"] is True
    assert payload["real_money_enabled"] is False
    assert (tmp_path / "OPEN_HQE_DASHBOARD_V6_VALIDATION_GOVERNANCE.cmd").exists()
    assert (tmp_path / "HQE_MASTER_SYSTEM_STATUS_DASHBOARD.html").exists()


def test_final_30_day_gate_holds_more_data(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_modules_231_250_common.py", "hqe_modules_231_250_common_gate")
    p = common.parser_for("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--trading-date", "2026-07-10", "--write"])
    payload = common.build_module(247, args)
    payload = common.emit_module(247, payload, args)
    assert payload["final_30_day_ready"] is False
    assert payload["real_money_allowed"] is False
    assert (tmp_path / "HQE_FINAL_30_DAY_READINESS_GATE.json").exists()


def test_paper_execution_gate_no_fake(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_modules_231_250_common.py", "hqe_modules_231_250_common_exec_gate")
    p = common.parser_for("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--trading-date", "2026-07-10", "--write"])
    payload = common.build_module(241, args)
    payload = common.emit_module(241, payload, args)
    assert payload["fake_trade_allowed"] is False
    assert payload["real_order_allowed"] is False
    assert payload["paper_execution_without_signal"] is False
