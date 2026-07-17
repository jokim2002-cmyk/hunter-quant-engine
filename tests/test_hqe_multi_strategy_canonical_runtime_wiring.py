from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
RUNTIME_PATH = SCRIPTS / "hqe_paper_product_runtime.py"


def load_runtime(name: str):
    spec = importlib.util.spec_from_file_location(name, RUNTIME_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def seed_legacy(runtime, workspace: Path, status: str = "FLAT") -> None:
    control = workspace / runtime.RUNTIME_FOLDER
    control.mkdir(parents=True, exist_ok=True)
    (control / runtime.MODULE_STATE_FILE).write_text(
        json.dumps({"status": status, "paper_only": True}),
        encoding="utf-8",
    )
    (control / runtime.MODULE_LEDGER_FILE).write_text(
        "timestamp,module,event,side,option_symbol,entry,stop_loss,target,exit_reason,paper_pnl,paper_only\n",
        encoding="utf-8",
    )


def enable(runtime, workspace: Path) -> None:
    from src.multi_strategy.canonical_runtime import (
        PHASE4_HUMAN_APPROVAL_PHRASE,
        prepare_canonical_runtime_cutover,
        write_human_gate,
    )

    write_human_gate(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        approval_phrase=PHASE4_HUMAN_APPROVAL_PHRASE,
    )
    prepare_canonical_runtime_cutover(
        workspace,
        runtime_folder=runtime.RUNTIME_FOLDER,
        runtime_state_file=runtime.RUNTIME_STATE_FILE,
        runtime_log_file=runtime.RUNTIME_LOG_FILE,
        stop_file=runtime.STOP_FILE,
        runtime_running=False,
    )


def test_runtime_source_imports_guarded_canonical_module():
    text = RUNTIME_PATH.read_text(encoding="utf-8")
    assert "prepare_canonical_runtime_cutover" in text
    assert "resolve_canonical_runtime_paths" in text
    assert "multi_strategy_runtime_snapshot" in text
    assert "REPO_ROOT" in text


def test_runtime_legacy_paths_unchanged_without_gate(tmp_path):
    runtime = load_runtime("phase4_runtime_legacy")
    paths = runtime.runtime_paths(tmp_path)
    control = tmp_path / runtime.RUNTIME_FOLDER
    assert paths["folder"] == control
    assert paths["state"] == control / runtime.MODULE_STATE_FILE
    assert paths["ledger"] == control / runtime.MODULE_LEDGER_FILE


def test_runtime_namespaces_state_ledger_summary_report_after_gate(tmp_path):
    runtime = load_runtime("phase4_runtime_namespaced")
    seed_legacy(runtime, tmp_path)
    enable(runtime, tmp_path)
    paths = runtime.runtime_paths(tmp_path)
    assert "strategies" in paths["state"].parts
    assert paths["state"].parent == paths["ledger"].parent
    assert paths["summary"].parent == paths["state"].parent
    assert paths["report"].parent == paths["state"].parent
    assert paths["runtime"].parent == tmp_path / runtime.RUNTIME_FOLDER


def test_runtime_status_exposes_strategy_identity(tmp_path):
    runtime = load_runtime("phase4_runtime_status")
    seed_legacy(runtime, tmp_path)
    enable(runtime, tmp_path)
    payload = runtime.status_payload(tmp_path)
    assert payload["multi_strategy_runtime_mode"] == "ONE_ACTIVE_STRATEGY_NAMESPACED"
    assert payload["strategy_id"] == "hqe_current_smc_compatibility"
    assert payload["multi_strategy_migration_complete"] is True
    assert payload["real_orders_allowed"] is False


def test_runtime_write_state_stays_control_plane_but_evidence_is_namespaced(tmp_path):
    runtime = load_runtime("phase4_runtime_write")
    seed_legacy(runtime, tmp_path)
    enable(runtime, tmp_path)
    payload = runtime.write_runtime(tmp_path, status="STOPPED_BY_OPERATOR")
    paths = runtime.runtime_paths(tmp_path)
    assert Path(payload["runtime_path"]) == paths["runtime"]
    assert Path(payload["state_path"]) == paths["state"]
    assert paths["runtime"].parent != paths["state"].parent
    stored = json.loads(paths["runtime"].read_text(encoding="utf-8"))
    assert stored["strategy_id"] == "hqe_current_smc_compatibility"


def test_runtime_snapshot_reads_namespaced_state(tmp_path):
    runtime = load_runtime("phase4_runtime_snapshot")
    seed_legacy(runtime, tmp_path)
    enable(runtime, tmp_path)
    paths = runtime.runtime_paths(tmp_path)
    paths["state"].write_text(
        json.dumps(
            {
                "status": "OPEN",
                "side": "PE_BUY",
                "option_symbol": "NSE:TESTPE",
                "entry": 100.0,
                "quantity": 1,
                "paper_only": True,
            }
        ),
        encoding="utf-8",
    )
    payload = runtime.paper_product_snapshot(tmp_path)
    assert payload["position_status"] == "OPEN"
    assert payload["side"] == "PE_BUY"
    assert payload["multi_strategy_runtime_mode"] == "ONE_ACTIVE_STRATEGY_NAMESPACED"


def test_runtime_guard_includes_phase4_safety_contract():
    runtime = load_runtime("phase4_runtime_guard")
    payload = runtime.guard_payload()
    guard = payload["multi_strategy_phase4_integration"]
    assert guard["guard_check_status"] == "PASS"
    assert guard["explicit_human_gate_required"] is True
    assert guard["real_orders_allowed"] is False
    assert guard["broker_execution_allowed"] is False


def test_invalid_gate_fails_closed_before_runtime_start(tmp_path):
    runtime = load_runtime("phase4_runtime_invalid_gate")
    control = tmp_path / runtime.RUNTIME_FOLDER
    control.mkdir(parents=True)
    (control / "HQE_MULTI_STRATEGY_PHASE4_HUMAN_GATE.json").write_text(
        '{"decision":"unsafe"}', encoding="utf-8"
    )
    args = argparse.Namespace(
        workspace=str(tmp_path),
        user_id="",
        symbol="NSE:NIFTY50-INDEX",
        interval_seconds=1,
        max_cycles=1,
        run_data_fetch=False,
    )
    with pytest.raises(Exception, match="gate"):
        runtime.run(args)
