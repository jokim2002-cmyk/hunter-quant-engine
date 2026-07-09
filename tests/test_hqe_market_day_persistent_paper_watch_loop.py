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


def test_guard_check_passes():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"), "--guard-check"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["guard_check_status"] == "PASS"
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["no_broker_execution"] is True


def test_once_creates_watch_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "dummy-client")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "dummy-token")
    (tmp_path / "FYERS_LIVE_DATA_ONLY_5M_NORMALIZED.csv").write_text(
        "datetime,open,high,low,close,volume,symbol,source\n2026-07-10T09:15:00+05:30,1,2,1,2,100,NSE:NIFTY50-INDEX,test\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"),
            "--workspace",
            str(tmp_path),
            "--trading-date",
            "2026-07-10",
            "--day-number",
            "1",
            "--symbol",
            "NSE:NIFTY50-INDEX",
            "--once",
            "--ignore-market-window",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "HQE PERSISTENT MARKET-DAY PAPER WATCH LOOP" in result.stdout
    csv_path = tmp_path / "DAY_001_PERSISTENT_PAPER_WATCH_LOOP.csv"
    assert csv_path.exists()
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig")))
    assert len(rows) == 1
    assert rows[0]["real_order_allowed"] == "NO"
    assert rows[0]["paper_trade_created"] == "NO"
    assert (tmp_path / "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json").exists()


def test_runner_installs_workspace_launcher(tmp_path):
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "scripts" / "RUN_MARKET_DAY_PERSISTENT_PAPER_WATCH.ps1"),
            "-Workspace",
            str(tmp_path),
            "-TradingDate",
            "2026-07-10",
            "-DayNumber",
            "1",
            "-InstallLauncher",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "INSTALLED_PERSISTENT_WATCH_LAUNCHER" in result.stdout
    launcher = tmp_path / "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd"
    assert launcher.exists()
    text = launcher.read_text(encoding="utf-8")
    assert "RUN_MARKET_DAY_PERSISTENT_PAPER_WATCH.ps1" in text
    assert "NO ORDERS" in text


def test_runner_once_finishes(tmp_path, monkeypatch):
    monkeypatch.setenv("FYERS_CLIENT_ID", "dummy-client")
    monkeypatch.setenv("FYERS_ACCESS_TOKEN", "dummy-token")
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "scripts" / "RUN_MARKET_DAY_PERSISTENT_PAPER_WATCH.ps1"),
            "-Workspace",
            str(tmp_path),
            "-TradingDate",
            "2026-07-10",
            "-DayNumber",
            "1",
            "-Once",
            "-IgnoreMarketWindow",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "PERSISTENT_MARKET_DAY_PAPER_WATCH_SAFE_RUN_COMPLETE" in result.stdout
    assert (tmp_path / "DAY_001_PERSISTENT_PAPER_WATCH_LOOP.csv").exists()
