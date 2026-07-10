from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_product_app_v2.py"


def load_module():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location(
        "hqe_product_app_v2_single_instance_test",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_canonical_watch_pid_prefers_root():
    module = load_module()
    processes = [
        {"pid": 25236, "parent_pid": 2004},
        {"pid": 15604, "parent_pid": 25236},
    ]
    assert module.canonical_watch_pid(processes) == 25236


def test_start_blocks_when_global_watch_exists(monkeypatch, tmp_path):
    module = load_module()
    controller = module.HiddenPaperWatchController(
        tmp_path,
        "hqe-user",
        "NSE:NIFTY50-INDEX",
    )

    monkeypatch.setattr(
        module,
        "find_existing_paper_watch_processes",
        lambda: [
            {"pid": 25236, "parent_pid": 2004},
            {"pid": 15604, "parent_pid": 25236},
        ],
    )

    def forbidden_popen(*args, **kwargs):
        raise AssertionError("subprocess.Popen must not be called")

    monkeypatch.setattr(module.subprocess, "Popen", forbidden_popen)

    result = controller.start()

    assert result["started"] is False
    assert result["status"] == "ALREADY_RUNNING_GLOBAL"
    assert result["pid"] == 25236
    assert result["process_count"] == 2


def test_global_watch_process_parser(monkeypatch):
    module = load_module()

    class Result:
        returncode = 0
        stdout = json.dumps(
            [
                {"ProcessId": 25236, "ParentProcessId": 2004},
                {"ProcessId": 15604, "ParentProcessId": 25236},
            ]
        )
        stderr = ""

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: Result())

    assert module.find_existing_paper_watch_processes() == [
        {"pid": 25236, "parent_pid": 2004},
        {"pid": 15604, "parent_pid": 25236},
    ]


def test_source_has_app_single_instance_mutex():
    text = SCRIPT.read_text(encoding="utf-8-sig")
    assert "HunterQuantEngineAppV2" in text
    assert "CreateMutexW" in text
    assert "acquire_app_single_instance()" in text
    assert "ALREADY_RUNNING_GLOBAL" in text
