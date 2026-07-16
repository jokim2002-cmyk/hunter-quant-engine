"""Read-only Module 131 migration planning and recovery compatibility.

This module reads legacy paper-runtime evidence, validates it, and produces a
deterministic migration plan. It never writes to the legacy runtime folder,
never writes to namespaced strategy storage, and cannot execute a migration.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import (
    LegacyMigrationError,
    LegacyRecoveryError,
    MigrationExecutionDisabledError,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import (
    PositionLifecycle,
    StrategyStateSnapshot,
)

MIGRATION_SCHEMA_VERSION = "1.0.0"
RECOVERY_SCHEMA_VERSION = "1.0.0"

LEGACY_STATE_FILENAME = "MODULE_131_POSITION_STATE.json"
LEGACY_LEDGER_FILENAME = "MODULE_131_PAPER_LEDGER.csv"
LEGACY_SUMMARY_FILENAME = "MODULE_131_SUPERVISOR_SUMMARY.json"
LEGACY_REPORT_FILENAME = "MODULE_131_INTRADAY_SUPERVISOR_REPORT.md"
LEGACY_REASON_LOG_FILENAME = "MODULE_131_SIGNAL_REASON_LOG.csv"
LEGACY_RUNTIME_FILENAME = "HQE_PAPER_PRODUCT_RUNTIME.json"

LEGACY_LEDGER_REQUIRED_COLUMNS = (
    "timestamp",
    "module",
    "event",
    "side",
    "option_symbol",
    "entry",
    "stop_loss",
    "target",
    "exit_reason",
    "paper_pnl",
    "paper_only",
)


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


def _stable_file_bytes(path: Path) -> tuple[bytes, int]:
    """Read one file and fail if it changes while being inspected."""

    try:
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise LegacyMigrationError(
            f"unable to read legacy evidence: {path}"
        ) from exc

    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise LegacyMigrationError(
            f"legacy evidence changed during read: {path}"
        )
    return data, after.st_mtime_ns


@dataclass(frozen=True)
class LegacyFileEvidence:
    """Immutable evidence identity for one legacy file."""

    path: str
    exists: bool
    size_bytes: int
    sha256: str
    modified_time_ns: int

    @classmethod
    def inspect(cls, path: str | Path) -> "LegacyFileEvidence":
        candidate = Path(path).resolve(strict=False)
        if not candidate.is_file():
            return cls(
                path=str(candidate),
                exists=False,
                size_bytes=0,
                sha256="",
                modified_time_ns=0,
            )
        data, modified = _stable_file_bytes(candidate)
        return cls(
            path=str(candidate),
            exists=True,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            modified_time_ns=modified,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "modified_time_ns": self.modified_time_ns,
        }


@dataclass(frozen=True)
class LegacyModule131Paths:
    """Known legacy product-runtime files under one runtime folder."""

    runtime_folder: Path
    runtime: Path
    state: Path
    ledger: Path
    summary: Path
    report: Path
    reason_log: Path

    @classmethod
    def from_runtime_folder(
        cls,
        runtime_folder: str | Path,
    ) -> "LegacyModule131Paths":
        root = Path(runtime_folder).resolve(strict=False)
        return cls(
            runtime_folder=root,
            runtime=root / LEGACY_RUNTIME_FILENAME,
            state=root / LEGACY_STATE_FILENAME,
            ledger=root / LEGACY_LEDGER_FILENAME,
            summary=root / LEGACY_SUMMARY_FILENAME,
            report=root / LEGACY_REPORT_FILENAME,
            reason_log=root / LEGACY_REASON_LOG_FILENAME,
        )

    def evidence(self) -> Mapping[str, LegacyFileEvidence]:
        return MappingProxyType(
            {
                "runtime": LegacyFileEvidence.inspect(self.runtime),
                "state": LegacyFileEvidence.inspect(self.state),
                "ledger": LegacyFileEvidence.inspect(self.ledger),
                "summary": LegacyFileEvidence.inspect(self.summary),
                "report": LegacyFileEvidence.inspect(self.report),
                "reason_log": LegacyFileEvidence.inspect(self.reason_log),
            }
        )


class MigrationReadiness(str, Enum):
    READY_FLAT = "READY_FLAT"
    NO_LEGACY_DATA = "NO_LEGACY_DATA"
    BLOCKED_RUNTIME_RUNNING = "BLOCKED_RUNTIME_RUNNING"
    BLOCKED_OPEN_POSITION = "BLOCKED_OPEN_POSITION"
    BLOCKED_CORRUPT_STATE = "BLOCKED_CORRUPT_STATE"
    BLOCKED_LEDGER_INCONSISTENT = "BLOCKED_LEDGER_INCONSISTENT"
    BLOCKED_SAFETY_VIOLATION = "BLOCKED_SAFETY_VIOLATION"


@dataclass(frozen=True)
class LegacyRuntimeObservation:
    status: str
    pid: int | None
    running_hint: bool
    payload_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "pid": self.pid,
            "running_hint": self.running_hint,
            "payload_hash": self.payload_hash,
        }


@dataclass(frozen=True)
class LegacyLedgerObservation:
    row_count: int
    opened_count: int
    closed_count: int
    unmatched_open_count: int
    row_hashes: tuple[str, ...]
    header: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "opened_count": self.opened_count,
            "closed_count": self.closed_count,
            "unmatched_open_count": self.unmatched_open_count,
            "row_hashes": list(self.row_hashes),
            "header": list(self.header),
        }


@dataclass(frozen=True)
class LegacyMigrationPlan:
    """Deterministic, non-executable migration plan."""

    selection_hash: str
    strategy_id: str
    strategy_version: str
    parameters_hash: str
    source_root: str
    readiness: MigrationReadiness
    evidence: Mapping[str, LegacyFileEvidence]
    runtime: LegacyRuntimeObservation
    ledger: LegacyLedgerObservation
    proposed_state: StrategyStateSnapshot
    legacy_state_status: str
    legacy_open_position: Mapping[str, Any] = field(default_factory=dict)
    issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: str = MIGRATION_SCHEMA_VERSION
    runtime_connected: bool = False
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != MIGRATION_SCHEMA_VERSION:
            raise LegacyMigrationError("unsupported migration schema version")
        if self.runtime_connected:
            raise LegacyMigrationError(
                "migration planner cannot be connected to runtime"
            )
        if self.execution_authorized:
            raise LegacyMigrationError(
                "Phase 4B migration execution must remain disabled"
            )
        if not self.selection_hash or not self.parameters_hash:
            raise LegacyMigrationError("migration selection identity is required")
        if not self.proposed_state.selection_hash == self.selection_hash:
            raise LegacyMigrationError(
                "proposed state does not match migration selection"
            )
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))
        object.__setattr__(
            self,
            "legacy_open_position",
            _freeze(self.legacy_open_position),
        )

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "selection_hash": self.selection_hash,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "parameters_hash": self.parameters_hash,
            "source_root": self.source_root,
            "readiness": self.readiness.value,
            "evidence": {
                key: value.to_dict()
                for key, value in sorted(self.evidence.items())
            },
            "runtime": self.runtime.to_dict(),
            "ledger": self.ledger.to_dict(),
            "proposed_state": self.proposed_state.to_dict(),
            "legacy_state_status": self.legacy_state_status,
            "legacy_open_position": dict(self.legacy_open_position),
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "runtime_connected": self.runtime_connected,
            "execution_authorized": self.execution_authorized,
        }

    @property
    def plan_hash(self) -> str:
        return canonical_mapping_hash(self._hash_payload())

    @property
    def migration_ready(self) -> bool:
        return self.readiness is MigrationReadiness.READY_FLAT

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._hash_payload(),
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True)
class LegacyRecoveryCompatibilitySnapshot:
    """In-memory restart-recovery representation of legacy state."""

    selection_hash: str
    plan_hash: str
    source_state_sha256: str
    source_ledger_sha256: str
    state: StrategyStateSnapshot
    runtime_connected: bool = False
    migration_complete: bool = False
    schema_version: str = RECOVERY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RECOVERY_SCHEMA_VERSION:
            raise LegacyRecoveryError("unsupported recovery schema version")
        if self.runtime_connected:
            raise LegacyRecoveryError(
                "recovery compatibility snapshot cannot connect to runtime"
            )
        if self.migration_complete:
            raise LegacyRecoveryError(
                "read-only recovery snapshot cannot mark migration complete"
            )
        if self.state.migration_complete:
            raise LegacyRecoveryError(
                "recovery state must remain migration-incomplete"
            )
        if self.state.selection_hash != self.selection_hash:
            raise LegacyRecoveryError(
                "recovery state selection identity mismatch"
            )

    @property
    def recovery_hash(self) -> str:
        return canonical_mapping_hash(
            {
                "schema_version": self.schema_version,
                "selection_hash": self.selection_hash,
                "plan_hash": self.plan_hash,
                "source_state_sha256": self.source_state_sha256,
                "source_ledger_sha256": self.source_ledger_sha256,
                "state": self.state.to_dict(),
                "runtime_connected": self.runtime_connected,
                "migration_complete": self.migration_complete,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "selection_hash": self.selection_hash,
            "plan_hash": self.plan_hash,
            "source_state_sha256": self.source_state_sha256,
            "source_ledger_sha256": self.source_ledger_sha256,
            "state": self.state.to_dict(),
            "runtime_connected": self.runtime_connected,
            "migration_complete": self.migration_complete,
            "recovery_hash": self.recovery_hash,
        }


def _parse_json_object(path: Path, label: str) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        return {}, ""
    data, _ = _stable_file_bytes(path)
    digest = hashlib.sha256(data).hexdigest()
    try:
        payload = json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LegacyMigrationError(
            f"{label} is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise LegacyMigrationError(f"{label} must contain a JSON object")
    return payload, digest


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _is_false(value: Any) -> bool:
    return str(value).strip().lower() in {"0", "false", "no", "n", ""}


def _observe_runtime(
    paths: LegacyModule131Paths,
) -> LegacyRuntimeObservation:
    if not paths.runtime.is_file():
        return LegacyRuntimeObservation(
            status="NOT_FOUND",
            pid=None,
            running_hint=False,
            payload_hash="",
        )
    payload, digest = _parse_json_object(
        paths.runtime, "legacy runtime state"
    )
    status = str(payload.get("status", "UNKNOWN")).strip().upper()
    pid = _safe_int(payload.get("pid"))
    running_hint = bool(payload.get("running", False))
    running_hint = (
        running_hint
        or status.startswith("RUNNING")
        or status in {"STARTING", "STOPPING"}
    )
    return LegacyRuntimeObservation(
        status=status,
        pid=pid,
        running_hint=running_hint,
        payload_hash=digest,
    )


def _validate_safety(payload: Mapping[str, Any]) -> tuple[str, ...]:
    issues: list[str] = []
    if payload and not bool(payload.get("paper_only", False)):
        issues.append("legacy state is not marked paper_only")
    for key in (
        "broker_execution_allowed",
        "real_orders_allowed",
        "auto_trading_allowed",
        "real_money_allowed",
    ):
        if bool(payload.get(key, False)):
            issues.append(f"legacy state has unsafe capability enabled: {key}")
    return tuple(issues)


def _open_position_from_state(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    issues: list[str] = []
    side = str(payload.get("side", "")).strip().upper()
    if side not in {"CE_BUY", "PE_BUY"}:
        issues.append("OPEN legacy state has invalid option side")
    entry = _safe_float(payload.get("entry"))
    stop_loss = _safe_float(payload.get("stop_loss"))
    target = _safe_float(payload.get("target"))
    quantity = _safe_int(payload.get("quantity"))
    if entry is None or entry <= 0:
        issues.append("OPEN legacy state has invalid entry")
    if stop_loss is None or stop_loss < 0:
        issues.append("OPEN legacy state has invalid stop_loss")
    if target is None or target <= 0:
        issues.append("OPEN legacy state has invalid target")
    if quantity is None or quantity <= 0:
        issues.append("OPEN legacy state has invalid quantity")

    position = {
        "side": side,
        "option_symbol": str(payload.get("option_symbol", "")),
        "candidate": str(payload.get("candidate", "")),
        "entry_time": str(payload.get("entry_time", "")),
        "entry": entry,
        "stop_loss": stop_loss,
        "target": target,
        "quantity": quantity,
    }
    return position, tuple(issues)


def _observe_ledger(
    paths: LegacyModule131Paths,
) -> LegacyLedgerObservation:
    if not paths.ledger.is_file():
        return LegacyLedgerObservation(
            row_count=0,
            opened_count=0,
            closed_count=0,
            unmatched_open_count=0,
            row_hashes=(),
            header=(),
        )

    data, _ = _stable_file_bytes(paths.ledger)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise LegacyMigrationError(
            "legacy ledger is not valid UTF-8"
        ) from exc

    reader = csv.DictReader(text.splitlines())
    header = tuple(reader.fieldnames or ())
    missing = [
        column
        for column in LEGACY_LEDGER_REQUIRED_COLUMNS
        if column not in header
    ]
    if missing:
        raise LegacyMigrationError(
            "legacy ledger is missing required columns: "
            + ", ".join(missing)
        )

    opened = 0
    closed = 0
    unmatched = 0
    hashes: list[str] = []

    for index, raw in enumerate(reader, start=1):
        row = {str(key): str(value or "") for key, value in raw.items()}
        hashes.append(canonical_mapping_hash(row))

        if str(row.get("module", "")).strip() not in {"131", "MODULE_131"}:
            raise LegacyMigrationError(
                f"legacy ledger row {index} has invalid module"
            )
        if not _is_true(row.get("paper_only")):
            raise LegacyMigrationError(
                f"legacy ledger row {index} is not paper-only"
            )

        event = row.get("event", "").strip().upper()
        side = row.get("side", "").strip().upper()
        if event not in {"POSITION_OPENED", "POSITION_CLOSED"}:
            raise LegacyMigrationError(
                f"legacy ledger row {index} has unsupported event"
            )
        if side not in {"CE_BUY", "PE_BUY"}:
            raise LegacyMigrationError(
                f"legacy ledger row {index} has invalid side"
            )
        if not row.get("timestamp", "").strip():
            raise LegacyMigrationError(
                f"legacy ledger row {index} has no timestamp"
            )
        for numeric in ("entry", "stop_loss", "target", "paper_pnl"):
            if _safe_float(row.get(numeric)) is None:
                raise LegacyMigrationError(
                    f"legacy ledger row {index} has invalid {numeric}"
                )

        if event == "POSITION_OPENED":
            opened += 1
            unmatched += 1
            if unmatched > 1:
                raise LegacyMigrationError(
                    "legacy ledger contains overlapping open positions"
                )
        else:
            closed += 1
            unmatched -= 1
            if unmatched < 0:
                raise LegacyMigrationError(
                    "legacy ledger closes a position before an open event"
                )

    return LegacyLedgerObservation(
        row_count=opened + closed,
        opened_count=opened,
        closed_count=closed,
        unmatched_open_count=unmatched,
        row_hashes=tuple(hashes),
        header=header,
    )


class LegacyModule131MigrationPlanner:
    """Build deterministic read-only plans from legacy Module 131 evidence."""

    def __init__(
        self,
        paths: LegacyModule131Paths,
        selection: StrategySelectionSnapshot,
        *,
        runtime_confirmed_stopped: bool = False,
    ) -> None:
        if selection.runtime_connected:
            raise LegacyMigrationError(
                "migration selection must remain disconnected from runtime"
            )
        self.paths = paths
        self.selection = selection
        self.runtime_confirmed_stopped = bool(runtime_confirmed_stopped)

    def build_plan(self) -> LegacyMigrationPlan:
        evidence_before = self.paths.evidence()
        runtime = _observe_runtime(self.paths)
        issues: list[str] = []
        warnings: list[str] = []

        any_legacy = any(item.exists for item in evidence_before.values())
        if not any_legacy:
            state = StrategyStateSnapshot.from_selection(
                self.selection,
                migration_complete=False,
            )
            return LegacyMigrationPlan(
                selection_hash=self.selection.selection_hash,
                strategy_id=self.selection.strategy_id,
                strategy_version=self.selection.strategy_version,
                parameters_hash=self.selection.parameters_hash,
                source_root=str(self.paths.runtime_folder),
                readiness=MigrationReadiness.NO_LEGACY_DATA,
                evidence=evidence_before,
                runtime=runtime,
                ledger=LegacyLedgerObservation(
                    row_count=0,
                    opened_count=0,
                    closed_count=0,
                    unmatched_open_count=0,
                    row_hashes=(),
                    header=(),
                ),
                proposed_state=state,
                legacy_state_status="NOT_FOUND",
                issues=("no legacy Module 131 evidence found",),
            )

        if runtime.running_hint and not self.runtime_confirmed_stopped:
            issues.append(
                "legacy paper runtime appears to be running; stop confirmation required"
            )
        elif runtime.running_hint and self.runtime_confirmed_stopped:
            warnings.append(
                "runtime state looked active but caller confirmed the process is stopped"
            )

        try:
            legacy_state, _ = _parse_json_object(
                self.paths.state, "legacy position state"
            )
        except LegacyMigrationError as exc:
            legacy_state = {}
            issues.append(str(exc))

        legacy_status = str(
            legacy_state.get("status", "MISSING")
        ).strip().upper()
        safety_issues = _validate_safety(legacy_state)
        issues.extend(safety_issues)

        position: dict[str, Any] = {}
        lifecycle = PositionLifecycle.FLAT
        if legacy_status == "OPEN":
            lifecycle = PositionLifecycle.OPEN
            position, position_issues = _open_position_from_state(
                legacy_state
            )
            issues.extend(position_issues)
        elif legacy_status == "FLAT":
            lifecycle = PositionLifecycle.FLAT
        elif legacy_status == "MISSING":
            issues.append("legacy position state is missing")
        else:
            issues.append(
                f"unsupported legacy position status '{legacy_status}'"
            )

        try:
            ledger = _observe_ledger(self.paths)
        except LegacyMigrationError as exc:
            ledger = LegacyLedgerObservation(
                row_count=0,
                opened_count=0,
                closed_count=0,
                unmatched_open_count=0,
                row_hashes=(),
                header=(),
            )
            issues.append(str(exc))

        if legacy_status == "FLAT" and ledger.unmatched_open_count != 0:
            issues.append(
                "legacy state is FLAT but ledger contains an unmatched open position"
            )
        if legacy_status == "OPEN" and ledger.row_count:
            if ledger.unmatched_open_count != 1:
                issues.append(
                    "legacy OPEN state does not match ledger open-position count"
                )

        proposed_state = StrategyStateSnapshot.from_selection(
            self.selection,
            lifecycle=lifecycle,
            position=position,
            last_event_id=(
                ledger.row_hashes[-1] if ledger.row_hashes else ""
            ),
            migration_complete=False,
        )

        if runtime.running_hint and not self.runtime_confirmed_stopped:
            readiness = MigrationReadiness.BLOCKED_RUNTIME_RUNNING
        elif safety_issues:
            readiness = MigrationReadiness.BLOCKED_SAFETY_VIOLATION
        elif legacy_status == "OPEN" and not issues:
            readiness = MigrationReadiness.BLOCKED_OPEN_POSITION
            issues.append(
                "legacy OPEN position must remain on the current runtime until closed"
            )
        elif any(
            "ledger" in issue.lower()
            or "overlapping" in issue.lower()
            or "closes a position" in issue.lower()
            for issue in issues
        ):
            readiness = MigrationReadiness.BLOCKED_LEDGER_INCONSISTENT
        elif issues:
            readiness = MigrationReadiness.BLOCKED_CORRUPT_STATE
        elif legacy_status == "OPEN":
            readiness = MigrationReadiness.BLOCKED_OPEN_POSITION
            issues.append(
                "legacy OPEN position must remain on the current runtime until closed"
            )
        else:
            readiness = MigrationReadiness.READY_FLAT

        evidence_after = self.paths.evidence()
        if {
            key: item.to_dict()
            for key, item in evidence_before.items()
        } != {
            key: item.to_dict()
            for key, item in evidence_after.items()
        }:
            raise LegacyMigrationError(
                "legacy evidence changed while migration plan was built"
            )

        return LegacyMigrationPlan(
            selection_hash=self.selection.selection_hash,
            strategy_id=self.selection.strategy_id,
            strategy_version=self.selection.strategy_version,
            parameters_hash=self.selection.parameters_hash,
            source_root=str(self.paths.runtime_folder),
            readiness=readiness,
            evidence=evidence_after,
            runtime=runtime,
            ledger=ledger,
            proposed_state=proposed_state,
            legacy_state_status=legacy_status,
            legacy_open_position=position,
            issues=tuple(issues),
            warnings=tuple(warnings),
        )


def build_recovery_compatibility_snapshot(
    plan: LegacyMigrationPlan,
    selection: StrategySelectionSnapshot,
) -> LegacyRecoveryCompatibilitySnapshot:
    """Return a non-writing recovery snapshot for review and parity tests."""

    if plan.selection_hash != selection.selection_hash:
        raise LegacyRecoveryError(
            "migration plan does not match requested selection"
        )
    if plan.proposed_state.selection_hash != selection.selection_hash:
        raise LegacyRecoveryError(
            "proposed recovery state does not match requested selection"
        )
    state_evidence = plan.evidence.get("state")
    ledger_evidence = plan.evidence.get("ledger")
    return LegacyRecoveryCompatibilitySnapshot(
        selection_hash=selection.selection_hash,
        plan_hash=plan.plan_hash,
        source_state_sha256=(
            state_evidence.sha256 if state_evidence else ""
        ),
        source_ledger_sha256=(
            ledger_evidence.sha256 if ledger_evidence else ""
        ),
        state=plan.proposed_state,
    )


def assert_migration_execution_allowed(
    plan: LegacyMigrationPlan,
) -> None:
    """Phase 4B deliberately has no migration executor."""

    raise MigrationExecutionDisabledError(
        "Phase 4B is read-only; migration execution is disabled "
        f"for plan {plan.plan_hash}"
    )
