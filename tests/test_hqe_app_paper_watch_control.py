from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load(name: str):
    path = SCRIPTS / "hqe_app_paper_watch_control.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runner_discovery_prefers_known_auto_runner(tmp_path):
    module = load("paper_watch_discovery")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    expected = scripts / "run_forward_paper_auto_runner.py"
    expected.write_text("print('x')\n", encoding="utf-8")
    assert module.discover_runner(tmp_path) == expected


def test_command_builder_uses_only_supported_safe_options(tmp_path):
    module = load("paper_watch_command")
    repo = tmp_path / "repo"
    runner = repo / "scripts" / "run_forward_paper_auto_runner.py"
    workspace = tmp_path / "workspace"
    help_text = (
        "usage: runner --workspace WORKSPACE [--paper-only] "
        "[--watch] [--write] [--poll-seconds N] [--user-id ID]"
    )
    command = module.build_runner_command(
        repo,
        runner,
        workspace,
        help_text,
    )
    joined = " ".join(command).lower()
    assert "--workspace" in joined
    assert "--paper-only" in joined
    assert "--watch" in joined
    assert "--write" in joined
    assert "--poll-seconds 30" in joined
    assert "--real" not in joined
    assert "--place-order" not in joined
    assert "--broker-execution" not in joined


def test_command_builder_requires_workspace(tmp_path):
    module = load("paper_watch_workspace_guard")
    try:
        module.build_runner_command(
            tmp_path,
            tmp_path / "runner.py",
            tmp_path / "workspace",
            "usage: runner [--watch]",
        )
    except RuntimeError as exc:
        assert "--workspace" in str(exc)
    else:
        raise AssertionError("Missing --workspace must be blocked.")


def test_guard_keeps_all_execution_locked():
    module = load("paper_watch_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["paper_process_control_only"] is True
    assert payload["real_money_enabled"] is False
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["option_selling_enabled"] is False


def test_app_contains_paper_watch_control_center():
    text = APP.read_text(encoding="utf-8-sig")
    assert "session_snapshot" in text
    assert "launch_watch_control_worker" in text
    assert "def refresh_paper_watch_center" in text
    assert "def open_paper_watch_center" in text
    assert "Paper-Watch Session Control" in text
    assert "Start Paper Watch" in text
    assert "Stop Paper Watch" in text
    assert "Open Latest Watch Log" in text
