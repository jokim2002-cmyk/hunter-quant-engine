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
    common = load_module(REPO / "scripts" / "hqe_modules_192_210_common.py", "hqe_modules_192_210_common")
    assert common.SAFETY_LOCK["paper_only"] is True
    assert common.SAFETY_LOCK["no_real_orders"] is True
    assert common.SAFETY_LOCK["no_broker_execution"] is True
    assert "place_order" in common.BLOCKED_ORDER_APIS
    assert len(common.MODULES) == 19


def test_all_module_guard_checks():
    common = load_module(REPO / "scripts" / "hqe_modules_192_210_common.py", "hqe_modules_192_210_common_guard")
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


def test_runner_creates_final_handoff(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "dummy-client")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "dummy-token")
    with (tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["trading_date", "day_number", "trade_count"])
        writer.writeheader()
        writer.writerow({"trading_date": "2026-07-10", "day_number": "1", "trade_count": "0"})

    module_173 = {
        "history_result": {
            "rows": 75,
            "response_redacted": {"s": "ok", "code": 200},
        }
    }
    (tmp_path / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json").write_text(json.dumps(module_173), encoding="utf-8")

    result = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO / "scripts" / "RUN_MODULES_192_210_MARKET_DAY_PAPER_WATCH_FINAL.ps1"),
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
    assert "MODULES_192_210_MARKET_DAY_PAPER_WATCH_SAFE_RUN_COMPLETE" in result.stdout
    final_json = tmp_path / "MODULE_210_MARKET_DAY_PAPER_WATCH_MASTER_HANDOFF_PACK_STATUS.json"
    assert final_json.exists()
    payload = json.loads(final_json.read_text(encoding="utf-8"))
    assert payload["module_status"] == "PASS"
    assert payload["modules_192_to_210_complete"] is True
    assert payload["real_money_enabled"] is False
    assert (tmp_path / "OPEN_HQE_VISUAL_DASHBOARD_V4_MARKET_WATCH.cmd").exists()
    assert (tmp_path / "HQE_MASTER_EVIDENCE_INDEX.html").exists()


def test_candidate_gate_blocks_real_orders(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_modules_192_210_common.py", "hqe_modules_192_210_common_gate")
    p = common.parser_for("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--trading-date", "2026-07-10", "--write"])
    payload = common.build_module(196, args)
    payload = common.emit_module(196, payload, args)
    assert payload["paper_trade_allowed_without_approved_signal"] is False
    assert payload["real_order_allowed"] is False
    assert (tmp_path / "DAY_001_PAPER_TRADE_CANDIDATE_GATE.json").exists()


def test_dashboard_v4_launcher_created(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_modules_192_210_common.py", "hqe_modules_192_210_common_v4")
    p = common.parser_for("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--trading-date", "2026-07-10", "--write"])
    payload = common.build_module(197, args)
    payload = common.emit_module(197, payload, args)
    assert payload["module_status"] == "PASS"
    assert (tmp_path / "OPEN_HQE_VISUAL_DASHBOARD_V4_MARKET_WATCH.cmd").exists()
    text = (tmp_path / "OPEN_HQE_VISUAL_DASHBOARD_V4_MARKET_WATCH.cmd").read_text(encoding="utf-8")
    assert "--launch" in text
