from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.canonical_runtime import (
    PHASE4_HUMAN_APPROVAL_PHRASE,
    PHASE4_RUNTIME_MODE_BLOCKED,
    PHASE4_RUNTIME_MODE_GATED,
    PHASE4_RUNTIME_MODE_LEGACY,
    HumanGateValidationError,
    RuntimeCutoverBlockedError,
    StrategySwitchBlockedError,
    assert_strategy_switch_allowed,
    build_human_gate_payload,
    calculate_gate_hash,
    current_smc_identity,
    guard_payload,
    integration_snapshot,
    prepare_canonical_runtime_cutover,
    read_json,
    resolve_canonical_runtime_paths,
    rollback_namespaced_cutover_to_legacy,
    sha256_file,
    validate_human_gate_payload,
    write_human_gate,
)

RUNTIME_FOLDER = "HQE_PAPER_PRODUCT_RUNTIME"
RUNTIME_STATE = "HQE_PAPER_PRODUCT_RUNTIME.json"
RUNTIME_LOG = "HQE_PAPER_PRODUCT_RUNTIME.log"
STOP_FILE = "HQE_PAPER_PRODUCT_STOP.flag"


def resolve(workspace: Path):
    return resolve_canonical_runtime_paths(
        workspace,
        runtime_folder=RUNTIME_FOLDER,
        runtime_state_file=RUNTIME_STATE,
        runtime_log_file=RUNTIME_LOG,
        stop_file=STOP_FILE,
    )


def prepare(workspace: Path, *, running: bool = False):
    return prepare_canonical_runtime_cutover(
        workspace,
        runtime_folder=RUNTIME_FOLDER,
        runtime_state_file=RUNTIME_STATE,
        runtime_log_file=RUNTIME_LOG,
        stop_file=STOP_FILE,
        runtime_running=running,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def seed_flat_legacy(workspace: Path) -> tuple[Path, Path]:
    control = workspace / RUNTIME_FOLDER
    state = control / "MODULE_131_POSITION_STATE.json"
    ledger = control / "MODULE_131_PAPER_LEDGER.csv"
    write_json(state, {"status": "FLAT", "paper_only": True})
    ledger.write_text(
        "timestamp,module,event,side,option_symbol,entry,stop_loss,target,exit_reason,paper_pnl,paper_only\n",
        encoding="utf-8",
    )
    return state, ledger


def seed_open_legacy(workspace: Path) -> tuple[Path, Path]:
    state, ledger = seed_flat_legacy(workspace)
    write_json(
        state,
        {
            "status": "OPEN",
            "side": "PE_BUY",
            "option_symbol": "NSE:TESTPE",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "quantity": 1,
            "entry_time": "2026-07-09T10:55:00",
            "paper_only": True,
        },
    )
    ledger.write_text(
        "timestamp,module,event,side,option_symbol,entry,stop_loss,target,exit_reason,paper_pnl,paper_only\n"
        "2026-07-09T10:55:00,131,POSITION_OPENED,PE_BUY,NSE:TESTPE,100.0,60.0,220.0,,0.0,True\n",
        encoding="utf-8",
    )
    return state, ledger


def write_valid_gate(workspace: Path):
    return write_human_gate(
        workspace,
        runtime_folder=RUNTIME_FOLDER,
        approval_phrase=PHASE4_HUMAN_APPROVAL_PHRASE,
        created_by="TEST_OPERATOR",
    )


def test_current_smc_identity_is_deterministic():
    first = current_smc_identity()
    second = current_smc_identity()
    assert first == second
    assert first["strategy_id"] == CURRENT_SMC_STRATEGY_ID
    assert first["strategy_version"] == CURRENT_SMC_STRATEGY_VERSION
    assert len(first["parameters_hash"]) == 64
    assert len(first["selection_hash"]) == 64


def test_human_gate_requires_exact_phrase():
    payload = build_human_gate_payload(approval_phrase="wrong")
    with pytest.raises(HumanGateValidationError, match="approval phrase"):
        validate_human_gate_payload(payload)


def test_human_gate_hash_detects_tampering():
    payload = build_human_gate_payload(
        approval_phrase=PHASE4_HUMAN_APPROVAL_PHRASE
    )
    assert payload["gate_hash"] == calculate_gate_hash(payload)
    payload["strategy_id"] = "tampered"
    with pytest.raises(HumanGateValidationError, match="strategy_id"):
        validate_human_gate_payload(payload)


def test_human_gate_rejects_unsafe_flag():
    payload = build_human_gate_payload(
        approval_phrase=PHASE4_HUMAN_APPROVAL_PHRASE
    )
    payload["real_orders_allowed"] = True
    payload["gate_hash"] = calculate_gate_hash(payload)
    with pytest.raises(HumanGateValidationError, match="real_orders_allowed"):
        validate_human_gate_payload(payload)


def test_missing_gate_uses_legacy_paths(tmp_path):
    paths = resolve(tmp_path)
    assert paths.mode == PHASE4_RUNTIME_MODE_LEGACY
    assert paths.gate_status == "MISSING"
    assert paths.state.parent == tmp_path / RUNTIME_FOLDER
    assert prepare(tmp_path)["status"] == "LEGACY_COMPATIBILITY_ACTIVE"


def test_invalid_gate_is_read_only_blocked(tmp_path):
    control = tmp_path / RUNTIME_FOLDER
    control.mkdir(parents=True)
    (control / "HQE_MULTI_STRATEGY_PHASE4_HUMAN_GATE.json").write_text(
        '{"decision":"tampered"}', encoding="utf-8"
    )
    paths = resolve(tmp_path)
    assert paths.mode == PHASE4_RUNTIME_MODE_BLOCKED
    assert paths.gate_status == "INVALID"
    with pytest.raises(HumanGateValidationError):
        prepare(tmp_path)


def test_valid_gate_routes_artifacts_to_strategy_namespace(tmp_path):
    write_valid_gate(tmp_path)
    paths = resolve(tmp_path)
    assert paths.mode == PHASE4_RUNTIME_MODE_GATED
    assert paths.gate_status == "VALID"
    assert CURRENT_SMC_STRATEGY_ID in str(paths.state)
    assert paths.runtime.parent == tmp_path / RUNTIME_FOLDER
    assert paths.state.parent != paths.runtime.parent


def test_prepare_cutover_copies_flat_legacy_evidence_atomically(tmp_path):
    source_state, source_ledger = seed_flat_legacy(tmp_path)
    source_hashes = (sha256_file(source_state), sha256_file(source_ledger))
    write_valid_gate(tmp_path)
    result = prepare(tmp_path)
    paths = resolve(tmp_path)
    assert result["status"] == "CUTOVER_PREPARED_PAPER_ONLY"
    assert sha256_file(paths.state) == source_hashes[0]
    assert sha256_file(paths.ledger) == source_hashes[1]
    assert sha256_file(source_state) == source_hashes[0]
    assert sha256_file(source_ledger) == source_hashes[1]
    assert paths.active_selection.is_file()
    assert paths.migration.is_file()
    assert paths.reconciliation.is_file()


def test_prepare_cutover_preserves_open_state_and_ledger(tmp_path):
    source_state, source_ledger = seed_open_legacy(tmp_path)
    source_hashes = (sha256_file(source_state), sha256_file(source_ledger))
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    paths = resolve(tmp_path)
    assert sha256_file(paths.state) == source_hashes[0]
    assert sha256_file(paths.ledger) == source_hashes[1]
    assert read_json(paths.state)["status"] == "OPEN"


def test_prepare_cutover_is_idempotent(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    first = prepare(tmp_path)
    second = prepare(tmp_path)
    assert first["migration"]["migration_hash"] == second["migration"]["migration_hash"]
    assert first["active_selection"]["selection_hash"] == second["active_selection"]["selection_hash"]


def test_prepare_cutover_blocks_existing_conflicting_target(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    paths = resolve(tmp_path)
    paths.state.parent.mkdir(parents=True, exist_ok=True)
    write_json(paths.state, {"status": "OPEN", "tampered": True})
    with pytest.raises(RuntimeCutoverBlockedError, match="differs"):
        prepare(tmp_path)


def test_prepare_cutover_blocks_running_runtime(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    with pytest.raises(RuntimeCutoverBlockedError, match="stopped"):
        prepare(tmp_path, running=True)


def test_active_selection_is_one_current_smc(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    paths = resolve(tmp_path)
    active = read_json(paths.active_selection)
    assert active["one_active_strategy"] is True
    assert active["strategy_id"] == CURRENT_SMC_STRATEGY_ID
    assert active["real_orders_allowed"] is False


def test_switch_blocked_while_runtime_running(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    with pytest.raises(StrategySwitchBlockedError, match="runtime"):
        assert_strategy_switch_allowed(
            tmp_path,
            runtime_folder=RUNTIME_FOLDER,
            requested_strategy_id=CURRENT_SMC_STRATEGY_ID,
            requested_strategy_version=CURRENT_SMC_STRATEGY_VERSION,
            runtime_running=True,
        )


def test_switch_blocked_while_position_open(tmp_path):
    seed_open_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    with pytest.raises(StrategySwitchBlockedError, match="position"):
        assert_strategy_switch_allowed(
            tmp_path,
            runtime_folder=RUNTIME_FOLDER,
            requested_strategy_id=CURRENT_SMC_STRATEGY_ID,
            requested_strategy_version=CURRENT_SMC_STRATEGY_VERSION,
            runtime_running=False,
        )


def test_unreviewed_strategy_switch_blocked_even_when_flat(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    with pytest.raises(StrategySwitchBlockedError, match="not reviewed"):
        assert_strategy_switch_allowed(
            tmp_path,
            runtime_folder=RUNTIME_FOLDER,
            requested_strategy_id="unreviewed",
            requested_strategy_version="9.9.9",
            runtime_running=False,
        )


def test_current_smc_noop_switch_allowed_when_flat_and_stopped(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    assert_strategy_switch_allowed(
        tmp_path,
        runtime_folder=RUNTIME_FOLDER,
        requested_strategy_id=CURRENT_SMC_STRATEGY_ID,
        requested_strategy_version=CURRENT_SMC_STRATEGY_VERSION,
        runtime_running=False,
    )


def test_rollback_blocked_when_open(tmp_path):
    seed_open_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    with pytest.raises(RuntimeCutoverBlockedError, match="position"):
        rollback_namespaced_cutover_to_legacy(
            tmp_path,
            runtime_folder=RUNTIME_FOLDER,
            runtime_state_file=RUNTIME_STATE,
            runtime_log_file=RUNTIME_LOG,
            stop_file=STOP_FILE,
            runtime_running=False,
        )


def test_rollback_blocked_when_runtime_running(tmp_path):
    seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    with pytest.raises(RuntimeCutoverBlockedError, match="running"):
        rollback_namespaced_cutover_to_legacy(
            tmp_path,
            runtime_folder=RUNTIME_FOLDER,
            runtime_state_file=RUNTIME_STATE,
            runtime_log_file=RUNTIME_LOG,
            stop_file=STOP_FILE,
            runtime_running=True,
        )


def test_flat_rollback_syncs_namespace_and_disables_gate(tmp_path):
    legacy_state, _ = seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    prepare(tmp_path)
    paths = resolve(tmp_path)
    write_json(paths.state, {"status": "FLAT", "cycle": 2, "paper_only": True})
    result = rollback_namespaced_cutover_to_legacy(
        tmp_path,
        runtime_folder=RUNTIME_FOLDER,
        runtime_state_file=RUNTIME_STATE,
        runtime_log_file=RUNTIME_LOG,
        stop_file=STOP_FILE,
        runtime_running=False,
    )
    assert result["rollback_complete"] is True
    assert read_json(legacy_state)["cycle"] == 2
    assert not paths.gate.exists()
    assert Path(result["disabled_gate"]).is_file()
    assert resolve(tmp_path).mode == PHASE4_RUNTIME_MODE_LEGACY


def test_integration_snapshot_reports_namespaced_identity(tmp_path):
    seed_flat_legacy(tmp_path)
    gate = write_valid_gate(tmp_path)
    prepare(tmp_path)
    payload = integration_snapshot(
        tmp_path,
        runtime_folder=RUNTIME_FOLDER,
        runtime_state_file=RUNTIME_STATE,
        runtime_log_file=RUNTIME_LOG,
        stop_file=STOP_FILE,
    )
    assert payload["multi_strategy_runtime_mode"] == PHASE4_RUNTIME_MODE_GATED
    assert payload["multi_strategy_gate_hash"] == gate["gate_hash"]
    assert payload["multi_strategy_one_active"] is True
    assert payload["strategy_id"] == CURRENT_SMC_STRATEGY_ID


def test_guard_payload_has_zero_execution_authority():
    payload = guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["one_active_strategy_enforced"] is True
    assert payload["explicit_human_gate_required"] is True
    assert payload["real_orders_allowed"] is False
    assert payload["broker_execution_allowed"] is False
    assert payload["real_money_allowed"] is False
    assert payload["option_selling_allowed"] is False


def test_runtime_restart_resumes_after_namespaced_state_changes(tmp_path):
    legacy_state, _ = seed_flat_legacy(tmp_path)
    write_valid_gate(tmp_path)
    first = prepare(tmp_path)
    paths = resolve(tmp_path)
    write_json(
        paths.state,
        {
            "status": "OPEN",
            "side": "PE_BUY",
            "entry": 100.0,
            "paper_only": True,
        },
    )
    assert read_json(legacy_state)["status"] == "FLAT"
    second = prepare(tmp_path)
    assert second["status"] == "CUTOVER_RESUMED_PAPER_ONLY"
    assert second["migration"]["migration_hash"] == first["migration"]["migration_hash"]
    assert read_json(paths.state)["status"] == "OPEN"
