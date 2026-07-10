from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_app_v2_controlled_dry_run_pack.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_controlled_dry_run_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_process_command_is_paper_watch_only(tmp_path):
    module = load_module()
    command = module.process_command(REPO, tmp_path, 30)

    joined = " ".join(command)
    assert "hqe_market_day_persistent_paper_watch_loop.py" in joined
    assert "--run-data-fetch" in command
    assert "--interval-seconds" in command
    assert "real-order" not in joined.lower()
    assert "broker-execution" not in joined.lower()


def test_changed_files_detects_create_and_modify():
    module = load_module()
    before = {
        "a": {"path": "a", "size_bytes": 1, "modified_ns": 10},
    }
    after = {
        "a": {"path": "a", "size_bytes": 2, "modified_ns": 11},
        "b": {"path": "b", "size_bytes": 1, "modified_ns": 12},
    }

    result = module.changed_files(before, after)

    assert result == [
        {"path": "a", "size_bytes": 2, "modified_ns": 11, "change": "MODIFIED"},
        {"path": "b", "size_bytes": 1, "modified_ns": 12, "change": "CREATED"},
    ]


def test_decision_pass_requires_preflight_and_all_runs():
    module = load_module()
    payload = module.build_decision(
        {"status": "PASS"},
        [{"status": "PASS"}, {"status": "PASS"}],
    )

    assert payload["dry_run_pack_status"] == "PASS"
    assert payload["decision"] == "APP_V2_CONTROLLED_DRY_RUNS_COMPLETE"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["auto_trading_enabled"] is False


def test_decision_holds_on_failed_run():
    module = load_module()
    payload = module.build_decision(
        {"status": "PASS"},
        [{"status": "PASS"}, {"status": "FAIL"}],
    )

    assert payload["dry_run_pack_status"] == "HOLD"
    assert payload["decision"] == "APP_V2_DRY_RUN_REPAIR_REQUIRED"
