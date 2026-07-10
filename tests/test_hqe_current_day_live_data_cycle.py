from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_current_day_live_data_cycle.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("hqe_current_day_live_data_cycle_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_live_cycle_restores_good_csv_on_failure(monkeypatch, tmp_path):
    module = load_module()
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    (repo / ".venv" / "Scripts").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    workspace.mkdir()

    csv_path = workspace / "FYERS_HISTORICAL_5M_DATA_ONLY_SAMPLE.csv"
    csv_path.write_text("good-current-day-data", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(*args, **kwargs):
        status = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
        status.write_text(json.dumps({
            "history_result": {
                "rows": 0,
                "response_redacted": {
                    "code": -16,
                    "s": "error",
                    "message": "Could not authenticate the user"
                }
            }
        }), encoding="utf-8")
        csv_path.write_text("bad-sample-schema", encoding="utf-8")
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    payload = module.run_cycle(repo, workspace, trading_date="2026-07-10")

    assert payload["cycle_status"] == "LIVE_DATA_CYCLE_FAILED_GOOD_CSV_PRESERVED"
    assert payload["restored_previous_csv"] is True
    assert csv_path.read_text(encoding="utf-8") == "good-current-day-data"


def test_live_cycle_requires_current_day_flag_command(monkeypatch, tmp_path):
    module = load_module()
    repo = tmp_path / "repo"
    workspace = tmp_path / "workspace"
    (repo / ".venv" / "Scripts").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    workspace.mkdir()
    captured = {}

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        status = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
        status.write_text(json.dumps({
            "history_result": {
                "rows": 1,
                "response_redacted": {
                    "code": 200,
                    "s": "ok",
                    "message": "",
                    "candles": [[1783655100, 1, 2, 0.5, 1.5, 10]]
                }
            }
        }), encoding="utf-8")
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    payload = module.run_cycle(repo, workspace, trading_date="2026-07-10")

    assert "--execute-live-data-only" in captured["command"]
    assert "--trading-date" in captured["command"]
    assert "2026-07-10" in captured["command"]
    assert payload["cycle_status"] == "LIVE_DATA_CYCLE_PASS"
