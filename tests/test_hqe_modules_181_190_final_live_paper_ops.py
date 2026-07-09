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


def test_common_guard_safety_lock():
    common = load_module(REPO / "scripts" / "hqe_ops_181_190_common.py", "hqe_ops_181_190_common")
    assert common.SAFETY_LOCK["paper_only"] is True
    assert common.SAFETY_LOCK["no_real_orders"] is True
    assert common.SAFETY_LOCK["no_broker_execution"] is True
    assert "place_order" in common.BLOCKED_ORDER_APIS


def test_module_181_writes_token_helper_launcher(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_ops_181_190_common.py", "common_181")
    mod = load_module(REPO / "scripts" / "hqe_fyers_token_refresh_helper_dashboard_integration.py", "m181")
    p = common.parser("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--write"])
    payload = mod.build(args)
    assert payload["module_status"] == "PASS"
    assert (tmp_path / "OPEN_HQE_FYERS_TOKEN_REFRESH_HELPER.cmd").exists()
    assert (REPO / "scripts" / "HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1").exists()


def test_all_modules_guard_check_subprocess():
    scripts = [
        "hqe_fyers_token_refresh_helper_dashboard_integration.py",
        "hqe_visual_dashboard_v2_launcher_fix.py",
        "hqe_fyers_data_only_health_monitor.py",
        "hqe_live_5m_normalized_data_bridge.py",
        "hqe_live_paper_signal_feed_bridge.py",
        "hqe_live_paper_session_controller.py",
        "hqe_visual_dashboard_v3_operator_app.py",
        "hqe_paper_live_daily_close_plan.py",
        "hqe_fyers_token_refresh_sop_pack.py",
        "hqe_live_paper_operation_final_close_pack.py",
    ]
    py = sys.executable
    for script in scripts:
        result = subprocess.run([py, str(REPO / "scripts" / script), "--guard-check"], capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
        assert payload["guard_check_status"] == "PASS"
        assert payload["safety_lock"]["no_real_orders"] is True


def test_runner_creates_status_files(tmp_path):
    day_ledger = tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv"
    with day_ledger.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["trading_date", "day_number", "trade_count"])
        writer.writeheader()
        writer.writerow({"trading_date": "2026-07-09", "day_number": "1", "trade_count": "0"})

    module_173 = {
        "history_result": {
            "rows": 2,
            "response_redacted": {
                "s": "ok",
                "code": 200,
                "candles": [[1783568700, 1, 2, 0.5, 1.5, 100], [1783569000, 1.5, 2.5, 1.0, 2.0, 200]],
            },
        }
    }
    (tmp_path / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json").write_text(json.dumps(module_173), encoding="utf-8")

    runner = REPO / "scripts" / "RUN_MODULES_181_190_FINAL_LIVE_PAPER_OPS.ps1"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(runner),
         "-Workspace", str(tmp_path), "-TradingDate", "2026-07-09", "-DayNumber", "1",
         "-UserId", "jokim-local", "-Symbol", "NSE:NIFTY50-INDEX"],
        capture_output=True, text=True, check=True,
    )
    assert "MODULES_181_190_SAFE_RUN_COMPLETE" in result.stdout
    assert (tmp_path / "MODULE_190_LIVE_PAPER_OPERATION_FINAL_CLOSE_STATUS.json").exists()
    payload = json.loads((tmp_path / "MODULE_190_LIVE_PAPER_OPERATION_FINAL_CLOSE_STATUS.json").read_text(encoding="utf-8"))
    assert payload["module_status"] == "PASS"
    assert payload["real_money_ready"] is False
    assert (tmp_path / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv").exists()


def test_visual_dashboard_v2_launcher_has_launch_flag(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_ops_181_190_common.py", "common_182")
    mod = load_module(REPO / "scripts" / "hqe_visual_dashboard_v2_launcher_fix.py", "m182")
    p = common.parser("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--write"])
    mod.build(args)
    text = (tmp_path / "OPEN_HQE_VISUAL_DASHBOARD_V2_LIVE_PAPER.cmd").read_text(encoding="utf-8")
    assert "--launch" in text
    assert "hqe_local_visual_dashboard_live_paper_v2.py" in text


def test_dashboard_v3_launcher_created(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    common = load_module(REPO / "scripts" / "hqe_ops_181_190_common.py", "common_187")
    mod = load_module(REPO / "scripts" / "hqe_visual_dashboard_v3_operator_app.py", "m187")
    p = common.parser("x")
    args = p.parse_args(["--workspace", str(tmp_path), "--write"])
    payload = mod.build(args)
    assert payload["module_status"] == "PASS"
    assert (tmp_path / "OPEN_HQE_VISUAL_DASHBOARD_V3_SAFE.cmd").exists()
    assert (tmp_path / "HQE_VISUAL_DASHBOARD_V3_STATUS.html").exists()
