"""Guarded canonical forward-paper integration for HQE multi-strategy.

This module provides the Phase 4 completion boundary.  It can route the
existing Module 131 paper lifecycle into one reviewed strategy namespace, but
only after an explicit deterministic human gate exists.  The current SMC
compatibility strategy is the only strategy that can be activated in this
phase.  All broker/order/real-money authority remains absent.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
    current_smc_manifest,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.registry import RegistrationStatus, StrategyRegistration
from src.multi_strategy.selection import StrategySelectionSnapshot

PHASE4_RUNTIME_SCHEMA_VERSION = "1.0.0"
PHASE4_GATE_FILENAME = "HQE_MULTI_STRATEGY_PHASE4_HUMAN_GATE.json"
PHASE4_ACTIVE_SELECTION_FILENAME = "HQE_MULTI_STRATEGY_ACTIVE_SELECTION.json"
PHASE4_MIGRATION_FILENAME = "HQE_MULTI_STRATEGY_PHASE4_MIGRATION.json"
PHASE4_ROLLBACK_FILENAME = "HQE_MULTI_STRATEGY_PHASE4_ROLLBACK.json"
PHASE4_RECONCILIATION_FILENAME = "HQE_MULTI_STRATEGY_PHASE4_RECONCILIATION.json"
PHASE4_SELECTION_FILENAME = "selection.json"
PHASE4_HUMAN_APPROVAL_PHRASE = "APPROVE PAPER-ONLY CURRENT SMC CUTOVER"
PHASE4_GATE_DECISION = "APPROVE_CURRENT_SMC_CANONICAL_PAPER_CUTOVER"
PHASE4_RUNTIME_MODE_LEGACY = "LEGACY_COMPATIBILITY"
PHASE4_RUNTIME_MODE_GATED = "ONE_ACTIVE_STRATEGY_NAMESPACED"
PHASE4_RUNTIME_MODE_BLOCKED = "BLOCKED_INVALID_HUMAN_GATE"

MODULE_STATE_FILE = "MODULE_131_POSITION_STATE.json"
MODULE_LEDGER_FILE = "MODULE_131_PAPER_LEDGER.csv"
MODULE_SUMMARY_FILE = "MODULE_131_SUPERVISOR_SUMMARY.json"
MODULE_REPORT_FILE = "MODULE_131_INTRADAY_SUPERVISOR_REPORT.md"
MODULE_REASON_LOG_FILE = "MODULE_131_SIGNAL_REASON_LOG.csv"

SAFETY = {
    "paper_only": True,
    "real_orders_allowed": False,
    "broker_execution_allowed": False,
    "auto_trading_allowed": False,
    "real_money_allowed": False,
    "option_selling_allowed": False,
}


class CanonicalRuntimeIntegrationError(RuntimeError):
    """Base fail-closed integration error."""


class HumanGateValidationError(CanonicalRuntimeIntegrationError):
    """Raised when the explicit human gate is absent or invalid for cutover."""


class RuntimeCutoverBlockedError(CanonicalRuntimeIntegrationError):
    """Raised when migration/cutover is unsafe."""


class StrategySwitchBlockedError(CanonicalRuntimeIntegrationError):
    """Raised when a strategy switch is not safe or reviewed."""


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    if not Path(path).is_file():
        return ""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not Path(path).is_file():
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, target)


def _copy_atomic(source: Path, destination: Path) -> None:
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(destination_path.name + ".tmp")
    shutil.copy2(source_path, temporary)
    os.replace(temporary, destination_path)


def reviewed_current_smc_selection() -> StrategySelectionSnapshot:
    manifest = current_smc_manifest()
    registration = StrategyRegistration(
        manifest=manifest,
        source="builtin-reviewed-current-smc",
        status=RegistrationStatus.EXECUTABLE_REVIEWED,
    )
    return StrategySelectionSnapshot.from_registration(registration)


def current_smc_identity() -> dict[str, Any]:
    selection = reviewed_current_smc_selection()
    manifest = current_smc_manifest()
    return {
        "strategy_id": CURRENT_SMC_STRATEGY_ID,
        "strategy_version": CURRENT_SMC_STRATEGY_VERSION,
        "implementation_key": CURRENT_SMC_IMPLEMENTATION_KEY,
        "manifest_fingerprint": manifest.fingerprint(),
        "parameters": dict(selection.parameters),
        "parameters_hash": selection.parameters_hash,
        "selection_hash": selection.selection_hash,
    }


def _gate_hash_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(payload.get("schema_version", "")),
        "decision": str(payload.get("decision", "")),
        "human_approval_phrase": str(payload.get("human_approval_phrase", "")),
        "created_at_utc": str(payload.get("created_at_utc", "")),
        "created_by": str(payload.get("created_by", "")),
        "strategy_id": str(payload.get("strategy_id", "")),
        "strategy_version": str(payload.get("strategy_version", "")),
        "implementation_key": str(payload.get("implementation_key", "")),
        "manifest_fingerprint": str(payload.get("manifest_fingerprint", "")),
        "parameters_hash": str(payload.get("parameters_hash", "")),
        "selection_hash": str(payload.get("selection_hash", "")),
        "paper_only": bool(payload.get("paper_only", False)),
        "real_orders_allowed": bool(payload.get("real_orders_allowed", True)),
        "broker_execution_allowed": bool(payload.get("broker_execution_allowed", True)),
        "auto_trading_allowed": bool(payload.get("auto_trading_allowed", True)),
        "real_money_allowed": bool(payload.get("real_money_allowed", True)),
        "option_selling_allowed": bool(payload.get("option_selling_allowed", True)),
    }


def calculate_gate_hash(payload: Mapping[str, Any]) -> str:
    return sha256_bytes(_canonical_json_bytes(_gate_hash_payload(payload)))


def build_human_gate_payload(
    *,
    approval_phrase: str,
    created_by: str = "HQE_OPERATOR",
) -> dict[str, Any]:
    identity = current_smc_identity()
    payload = {
        "schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "decision": PHASE4_GATE_DECISION,
        "human_approval_phrase": str(approval_phrase),
        "created_at_utc": utc_now_text(),
        "created_by": str(created_by),
        **identity,
        **SAFETY,
    }
    payload["gate_hash"] = calculate_gate_hash(payload)
    return payload


def validate_human_gate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    identity = current_smc_identity()
    if str(payload.get("schema_version", "")) != PHASE4_RUNTIME_SCHEMA_VERSION:
        issues.append("unsupported gate schema_version")
    if str(payload.get("decision", "")) != PHASE4_GATE_DECISION:
        issues.append("gate decision is not approved")
    if str(payload.get("human_approval_phrase", "")) != PHASE4_HUMAN_APPROVAL_PHRASE:
        issues.append("human approval phrase does not match")
    for key in (
        "strategy_id",
        "strategy_version",
        "implementation_key",
        "manifest_fingerprint",
        "parameters_hash",
        "selection_hash",
    ):
        if str(payload.get(key, "")) != str(identity[key]):
            issues.append(f"{key} does not match reviewed current SMC")
    for key in (
        "paper_only",
        "real_orders_allowed",
        "broker_execution_allowed",
        "auto_trading_allowed",
        "real_money_allowed",
        "option_selling_allowed",
    ):
        if payload.get(key) is not SAFETY[key]:
            issues.append(f"unsafe gate safety flag: {key}")
    supplied_hash = str(payload.get("gate_hash", ""))
    expected_hash = calculate_gate_hash(payload)
    if not supplied_hash or supplied_hash != expected_hash:
        issues.append("gate_hash does not match gate contents")
    if issues:
        raise HumanGateValidationError("; ".join(issues))
    return dict(payload)


@dataclass(frozen=True)
class CanonicalRuntimePaths:
    workspace: Path
    control_directory: Path
    legacy_directory: Path
    namespace_directory: Path
    runtime: Path
    log: Path
    stop: Path
    state: Path
    ledger: Path
    summary: Path
    report: Path
    reason_log: Path
    gate: Path
    active_selection: Path
    migration: Path
    rollback: Path
    reconciliation: Path
    selection: Path
    mode: str
    gate_status: str
    gate_hash: str

    def runtime_mapping(self) -> dict[str, Path]:
        return {
            "folder": self.namespace_directory,
            "runtime": self.runtime,
            "log": self.log,
            "stop": self.stop,
            "state": self.state,
            "ledger": self.ledger,
            "summary": self.summary,
            "report": self.report,
        }


def _control_directory(workspace: Path, runtime_folder: str) -> Path:
    return Path(workspace).resolve() / runtime_folder


def _namespace_directory(control: Path) -> Path:
    identity = current_smc_identity()
    return (
        control
        / "strategies"
        / identity["strategy_id"]
        / identity["strategy_version"]
        / identity["parameters_hash"]
    )


def resolve_canonical_runtime_paths(
    workspace: Path,
    *,
    runtime_folder: str,
    runtime_state_file: str,
    runtime_log_file: str,
    stop_file: str,
) -> CanonicalRuntimePaths:
    workspace_path = Path(workspace).resolve()
    control = _control_directory(workspace_path, runtime_folder)
    legacy = control
    namespace = _namespace_directory(control)
    gate_path = control / PHASE4_GATE_FILENAME
    gate_payload = read_json(gate_path)
    gate_status = "MISSING"
    gate_hash = ""
    mode = PHASE4_RUNTIME_MODE_LEGACY
    active_directory = legacy

    if gate_path.is_file():
        try:
            validated = validate_human_gate_payload(gate_payload)
        except HumanGateValidationError:
            gate_status = "INVALID"
            mode = PHASE4_RUNTIME_MODE_BLOCKED
            active_directory = legacy
        else:
            gate_status = "VALID"
            gate_hash = str(validated["gate_hash"])
            mode = PHASE4_RUNTIME_MODE_GATED
            active_directory = namespace

    return CanonicalRuntimePaths(
        workspace=workspace_path,
        control_directory=control,
        legacy_directory=legacy,
        namespace_directory=active_directory,
        runtime=control / runtime_state_file,
        log=control / runtime_log_file,
        stop=control / stop_file,
        state=active_directory / MODULE_STATE_FILE,
        ledger=active_directory / MODULE_LEDGER_FILE,
        summary=active_directory / MODULE_SUMMARY_FILE,
        report=active_directory / MODULE_REPORT_FILE,
        reason_log=active_directory / MODULE_REASON_LOG_FILE,
        gate=gate_path,
        active_selection=control / PHASE4_ACTIVE_SELECTION_FILENAME,
        migration=namespace / PHASE4_MIGRATION_FILENAME,
        rollback=control / PHASE4_ROLLBACK_FILENAME,
        reconciliation=namespace / PHASE4_RECONCILIATION_FILENAME,
        selection=namespace / PHASE4_SELECTION_FILENAME,
        mode=mode,
        gate_status=gate_status,
        gate_hash=gate_hash,
    )


def integration_snapshot(
    workspace: Path,
    *,
    runtime_folder: str,
    runtime_state_file: str,
    runtime_log_file: str,
    stop_file: str,
) -> dict[str, Any]:
    paths = resolve_canonical_runtime_paths(
        workspace,
        runtime_folder=runtime_folder,
        runtime_state_file=runtime_state_file,
        runtime_log_file=runtime_log_file,
        stop_file=stop_file,
    )
    identity = current_smc_identity()
    active_selection = read_json(paths.active_selection)
    migration = read_json(paths.migration)
    state = read_json(paths.state)
    lifecycle = str(state.get("status", "FLAT") or "FLAT").upper()
    if lifecycle not in {"OPEN", "HELD", "CLOSED", "FLAT"}:
        lifecycle = "FLAT"
    return {
        "multi_strategy_phase4_schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "multi_strategy_runtime_mode": paths.mode,
        "multi_strategy_gate_status": paths.gate_status,
        "multi_strategy_gate_hash": paths.gate_hash,
        "multi_strategy_gate_path": str(paths.gate),
        "multi_strategy_active_selection_path": str(paths.active_selection),
        "multi_strategy_namespace": str(paths.namespace_directory),
        "multi_strategy_migration_path": str(paths.migration),
        "multi_strategy_migration_complete": bool(
            migration.get("migration_complete", False)
        ),
        "multi_strategy_one_active": bool(active_selection),
        "multi_strategy_lifecycle": lifecycle,
        **identity,
        **SAFETY,
    }


def write_human_gate(
    workspace: Path,
    *,
    runtime_folder: str,
    approval_phrase: str,
    created_by: str = "HQE_OPERATOR",
) -> dict[str, Any]:
    control = _control_directory(Path(workspace), runtime_folder)
    control.mkdir(parents=True, exist_ok=True)
    payload = build_human_gate_payload(
        approval_phrase=approval_phrase,
        created_by=created_by,
    )
    validate_human_gate_payload(payload)
    write_json_atomic(control / PHASE4_GATE_FILENAME, payload)
    return payload


def _source_target_pairs(paths: CanonicalRuntimePaths) -> tuple[tuple[Path, Path], ...]:
    namespace = _namespace_directory(paths.control_directory)
    return (
        (paths.legacy_directory / MODULE_STATE_FILE, namespace / MODULE_STATE_FILE),
        (paths.legacy_directory / MODULE_LEDGER_FILE, namespace / MODULE_LEDGER_FILE),
        (paths.legacy_directory / MODULE_SUMMARY_FILE, namespace / MODULE_SUMMARY_FILE),
        (paths.legacy_directory / MODULE_REPORT_FILE, namespace / MODULE_REPORT_FILE),
        (paths.legacy_directory / MODULE_REASON_LOG_FILE, namespace / MODULE_REASON_LOG_FILE),
    )


def _state_lifecycle(path: Path) -> str:
    state = read_json(path)
    status = str(state.get("status", "FLAT") or "FLAT").upper()
    if status in {"OPEN", "HELD"}:
        return "OPEN"
    if status == "CLOSED":
        return "CLOSED"
    return "FLAT"


def _ledger_balance(path: Path) -> dict[str, int]:
    if not Path(path).is_file():
        return {"opened": 0, "closed": 0, "open_balance": 0}
    opened = 0
    closed = 0
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                event = str(row.get("event", "")).upper()
                if event == "POSITION_OPENED":
                    opened += 1
                elif event == "POSITION_CLOSED":
                    closed += 1
    except (OSError, csv.Error):
        return {"opened": -1, "closed": -1, "open_balance": -1}
    return {
        "opened": opened,
        "closed": closed,
        "open_balance": max(0, opened - closed),
    }


def reconcile_legacy_and_namespace(paths: CanonicalRuntimePaths) -> dict[str, Any]:
    namespace = _namespace_directory(paths.control_directory)
    legacy_state = paths.legacy_directory / MODULE_STATE_FILE
    namespaced_state = namespace / MODULE_STATE_FILE
    legacy_ledger = paths.legacy_directory / MODULE_LEDGER_FILE
    namespaced_ledger = namespace / MODULE_LEDGER_FILE
    source_hashes = {
        "state": sha256_file(legacy_state),
        "ledger": sha256_file(legacy_ledger),
    }
    target_hashes = {
        "state": sha256_file(namespaced_state),
        "ledger": sha256_file(namespaced_ledger),
    }
    lifecycle_match = _state_lifecycle(legacy_state) == _state_lifecycle(
        namespaced_state
    )
    ledger_match = _ledger_balance(legacy_ledger) == _ledger_balance(
        namespaced_ledger
    )
    exact_copy_match = all(
        not source_hashes[key] or source_hashes[key] == target_hashes[key]
        for key in source_hashes
    )
    payload = {
        "schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "generated_at_utc": utc_now_text(),
        "strategy_id": CURRENT_SMC_STRATEGY_ID,
        "strategy_version": CURRENT_SMC_STRATEGY_VERSION,
        "source_hashes": source_hashes,
        "target_hashes": target_hashes,
        "legacy_lifecycle": _state_lifecycle(legacy_state),
        "namespaced_lifecycle": _state_lifecycle(namespaced_state),
        "legacy_ledger_balance": _ledger_balance(legacy_ledger),
        "namespaced_ledger_balance": _ledger_balance(namespaced_ledger),
        "lifecycle_match": lifecycle_match,
        "ledger_match": ledger_match,
        "exact_copy_match": exact_copy_match,
        "reconciliation_status": (
            "MATCHED_INITIAL_MIGRATION"
            if lifecycle_match and ledger_match and exact_copy_match
            else "DIVERGED"
        ),
        **SAFETY,
    }
    payload["reconciliation_hash"] = canonical_mapping_hash(payload)
    return payload


def prepare_canonical_runtime_cutover(
    workspace: Path,
    *,
    runtime_folder: str,
    runtime_state_file: str,
    runtime_log_file: str,
    stop_file: str,
    runtime_running: bool,
) -> dict[str, Any]:
    paths = resolve_canonical_runtime_paths(
        workspace,
        runtime_folder=runtime_folder,
        runtime_state_file=runtime_state_file,
        runtime_log_file=runtime_log_file,
        stop_file=stop_file,
    )
    if paths.gate_status == "MISSING":
        return {
            "status": "LEGACY_COMPATIBILITY_ACTIVE",
            "cutover_prepared": False,
            "runtime_mode": PHASE4_RUNTIME_MODE_LEGACY,
            **integration_snapshot(
                workspace,
                runtime_folder=runtime_folder,
                runtime_state_file=runtime_state_file,
                runtime_log_file=runtime_log_file,
                stop_file=stop_file,
            ),
        }
    if paths.gate_status != "VALID":
        raise HumanGateValidationError("invalid Phase 4 human gate")
    if runtime_running:
        raise RuntimeCutoverBlockedError("runtime must be stopped before cutover")

    identity = current_smc_identity()
    namespace = _namespace_directory(paths.control_directory)
    namespace.mkdir(parents=True, exist_ok=True)

    existing_migration = read_json(namespace / PHASE4_MIGRATION_FILENAME)
    existing_selection = read_json(paths.active_selection)
    if existing_migration.get("migration_complete") is True:
        expected_identity = all(
            str(existing_migration.get(key, "")) == str(identity[key])
            for key in (
                "strategy_id",
                "strategy_version",
                "implementation_key",
                "manifest_fingerprint",
                "parameters_hash",
                "selection_hash",
            )
        )
        selection_matches = (
            existing_selection.get("one_active_strategy") is True
            and str(existing_selection.get("gate_hash", "")) == paths.gate_hash
            and all(
                str(existing_selection.get(key, "")) == str(identity[key])
                for key in (
                    "strategy_id",
                    "strategy_version",
                    "implementation_key",
                    "manifest_fingerprint",
                    "parameters_hash",
                    "selection_hash",
                )
            )
        )
        required_namespaced = (
            namespace / PHASE4_SELECTION_FILENAME,
            namespace / PHASE4_MIGRATION_FILENAME,
        )
        if (
            not expected_identity
            or str(existing_migration.get("gate_hash", "")) != paths.gate_hash
            or not selection_matches
            or not all(path.is_file() for path in required_namespaced)
        ):
            raise RuntimeCutoverBlockedError(
                "existing migration identity or gate binding is invalid"
            )
        return {
            "status": "CUTOVER_RESUMED_PAPER_ONLY",
            "cutover_prepared": True,
            "runtime_mode": PHASE4_RUNTIME_MODE_GATED,
            "migration": existing_migration,
            "reconciliation": read_json(
                namespace / PHASE4_RECONCILIATION_FILENAME
            ),
            "active_selection": existing_selection,
            **SAFETY,
        }

    copied: list[dict[str, Any]] = []
    for source, target in _source_target_pairs(paths):
        source_hash = sha256_file(source)
        target_hash = sha256_file(target)
        if source_hash and target_hash and source_hash != target_hash:
            raise RuntimeCutoverBlockedError(
                f"existing namespaced target differs: {target.name}"
            )
        if source_hash and not target_hash:
            _copy_atomic(source, target)
            target_hash = sha256_file(target)
            if source_hash != target_hash:
                raise RuntimeCutoverBlockedError(
                    f"atomic migration hash mismatch: {source.name}"
                )
        copied.append(
            {
                "source": str(source),
                "target": str(target),
                "source_sha256": source_hash,
                "target_sha256": target_hash,
                "copied": bool(source_hash),
            }
        )

    selection_payload = {
        "schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "activation_mode": PHASE4_RUNTIME_MODE_GATED,
        "one_active_strategy": True,
        "activated_at_utc": utc_now_text(),
        "gate_hash": paths.gate_hash,
        **identity,
        **SAFETY,
    }
    selection_payload["active_selection_hash"] = canonical_mapping_hash(
        selection_payload
    )
    write_json_atomic(paths.active_selection, selection_payload)
    write_json_atomic(namespace / PHASE4_SELECTION_FILENAME, selection_payload)

    reconciliation = reconcile_legacy_and_namespace(paths)
    if reconciliation["reconciliation_status"] != "MATCHED_INITIAL_MIGRATION":
        raise RuntimeCutoverBlockedError("initial migration reconciliation failed")
    write_json_atomic(namespace / PHASE4_RECONCILIATION_FILENAME, reconciliation)

    migration_payload = {
        "schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "migration_complete": True,
        "migration_mode": "ATOMIC_COPY_PRESERVE_LEGACY_SOURCE",
        "migrated_at_utc": utc_now_text(),
        "gate_hash": paths.gate_hash,
        "active_selection_hash": selection_payload["active_selection_hash"],
        "files": copied,
        "reconciliation_hash": reconciliation["reconciliation_hash"],
        **identity,
        **SAFETY,
    }
    migration_payload["migration_hash"] = canonical_mapping_hash(
        migration_payload
    )
    write_json_atomic(namespace / PHASE4_MIGRATION_FILENAME, migration_payload)

    return {
        "status": "CUTOVER_PREPARED_PAPER_ONLY",
        "cutover_prepared": True,
        "runtime_mode": PHASE4_RUNTIME_MODE_GATED,
        "migration": migration_payload,
        "reconciliation": reconciliation,
        "active_selection": selection_payload,
        **SAFETY,
    }


def assert_strategy_switch_allowed(
    workspace: Path,
    *,
    runtime_folder: str,
    requested_strategy_id: str,
    requested_strategy_version: str,
    runtime_running: bool,
) -> None:
    if runtime_running:
        raise StrategySwitchBlockedError("strategy switch blocked while runtime is running")
    control = _control_directory(Path(workspace), runtime_folder)
    namespace = _namespace_directory(control)
    state = read_json(namespace / MODULE_STATE_FILE)
    if str(state.get("status", "FLAT")).upper() in {"OPEN", "HELD"}:
        raise StrategySwitchBlockedError("strategy switch blocked while a position is open")
    if (
        requested_strategy_id != CURRENT_SMC_STRATEGY_ID
        or requested_strategy_version != CURRENT_SMC_STRATEGY_VERSION
    ):
        raise StrategySwitchBlockedError(
            "requested strategy is not reviewed for canonical Phase 4 activation"
        )


def rollback_namespaced_cutover_to_legacy(
    workspace: Path,
    *,
    runtime_folder: str,
    runtime_state_file: str,
    runtime_log_file: str,
    stop_file: str,
    runtime_running: bool,
) -> dict[str, Any]:
    paths = resolve_canonical_runtime_paths(
        workspace,
        runtime_folder=runtime_folder,
        runtime_state_file=runtime_state_file,
        runtime_log_file=runtime_log_file,
        stop_file=stop_file,
    )
    if paths.gate_status != "VALID":
        raise RuntimeCutoverBlockedError("no valid namespaced cutover is active")
    if runtime_running:
        raise RuntimeCutoverBlockedError("rollback blocked while runtime is running")
    namespace = _namespace_directory(paths.control_directory)
    state = read_json(namespace / MODULE_STATE_FILE)
    if str(state.get("status", "FLAT")).upper() in {"OPEN", "HELD"}:
        raise RuntimeCutoverBlockedError("rollback blocked while a position is open")

    backup_root = paths.control_directory / "phase4_rollback_backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    restored: list[dict[str, str]] = []
    for legacy_source, namespaced_source in (
        (paths.legacy_directory / MODULE_STATE_FILE, namespace / MODULE_STATE_FILE),
        (paths.legacy_directory / MODULE_LEDGER_FILE, namespace / MODULE_LEDGER_FILE),
        (paths.legacy_directory / MODULE_SUMMARY_FILE, namespace / MODULE_SUMMARY_FILE),
        (paths.legacy_directory / MODULE_REPORT_FILE, namespace / MODULE_REPORT_FILE),
        (paths.legacy_directory / MODULE_REASON_LOG_FILE, namespace / MODULE_REASON_LOG_FILE),
    ):
        if legacy_source.is_file():
            _copy_atomic(legacy_source, backup_root / legacy_source.name)
        if namespaced_source.is_file():
            _copy_atomic(namespaced_source, legacy_source)
        restored.append(
            {
                "legacy": str(legacy_source),
                "namespaced": str(namespaced_source),
                "legacy_sha256_after": sha256_file(legacy_source),
                "namespaced_sha256": sha256_file(namespaced_source),
            }
        )

    disabled_gate = paths.gate.with_suffix(paths.gate.suffix + ".disabled")
    if disabled_gate.exists():
        disabled_gate.unlink()
    os.replace(paths.gate, disabled_gate)

    payload = {
        "schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "rollback_complete": True,
        "rolled_back_at_utc": utc_now_text(),
        "disabled_gate": str(disabled_gate),
        "backup_root": str(backup_root),
        "files": restored,
        **current_smc_identity(),
        **SAFETY,
    }
    payload["rollback_hash"] = canonical_mapping_hash(payload)
    write_json_atomic(paths.control_directory / PHASE4_ROLLBACK_FILENAME, payload)
    return payload


def guard_payload() -> dict[str, Any]:
    return {
        "schema_version": PHASE4_RUNTIME_SCHEMA_VERSION,
        "guard_check_status": "PASS",
        "current_smc_only": True,
        "explicit_human_gate_required": True,
        "one_active_strategy_enforced": True,
        "runtime_stopped_before_cutover_required": True,
        "open_position_switch_blocked": True,
        "runtime_running_switch_blocked": True,
        "legacy_source_preserved_during_migration": True,
        "atomic_namespaced_migration": True,
        "restart_recovery_uses_namespaced_state": True,
        "rollback_requires_flat_and_stopped": True,
        **SAFETY,
    }
