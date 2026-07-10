from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_fyers_live_fetch_diagnostic.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_fyers_live_fetch_diagnostic_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def process_fixture():
    return [
        {
            "ProcessId": 200,
            "ParentProcessId": 99,
            "Name": "python.exe",
            "ExecutablePath": "venv-python.exe",
            "CommandLine": "watch",
        },
        {
            "ProcessId": 201,
            "ParentProcessId": 200,
            "Name": "python.exe",
            "ExecutablePath": "python.exe",
            "CommandLine": "watch",
        },
    ]


def test_canonical_python_process_uses_root():
    module = load_module()
    payload = module.canonical_python_watch_process(process_fixture())
    assert payload["canonical_pid"] == 200
    assert payload["process_count"] == 2
    assert payload["reason"] == "ROOT_PYTHON_WATCH_PROCESS"


def test_build_command_uses_supported_arguments(tmp_path):
    module = load_module()
    command = module.build_command(
        Path("python.exe"),
        Path("fetcher.py"),
        tmp_path,
        "--workspace --symbol --user-id",
    )
    assert "--workspace" in command
    assert "--symbol" in command
    assert "--user-id" in command


def test_classify_completed_but_csv_unchanged():
    module = load_module()
    payload = module.classify(
        {"timed_out": False, "returncode": 0},
        {"status": "DATA_ONLY_HISTORY_CALL_COMPLETED"},
        False,
    )
    assert payload["decision"] == "FETCH_REPORTED_COMPLETE_BUT_CSV_UNCHANGED"


def test_classify_csv_updated():
    module = load_module()
    payload = module.classify(
        {"timed_out": False, "returncode": 0},
        {"status": "PASS"},
        True,
    )
    assert payload["decision"] == "FETCH_UPDATED_CSV"
