"""Guarded namespaced lifecycle writes for the reviewed current HQE SMC.

This module authorizes writes only inside an explicit Phase 4K sandbox root.
It never writes canonical runtime, selection, state, ledger, broker, or license
artifacts. The authoritative lifecycle bundle and its state/ledger projections
are transactional at process level and protected by an exclusive lock.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.lifecycle_adapter import (
    DisabledCanonicalLifecycleAdapter,
    DisabledCanonicalLifecyclePlan,
    DisabledLifecyclePlanStatus,
)
from src.multi_strategy.lifecycle_journal import (
    LifecycleJournalError,
    SandboxLifecycleBundle,
    SandboxLifecycleEvent,
    read_bundle,
    state_hash,
    write_bundle_atomic,
)
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import (
    LEDGER_COLUMNS,
    PositionLifecycle,
    StrategyArtifactPaths,
    StrategyStateSnapshot,
)

LIFECYCLE_WRITE_SANDBOX_SCHEMA_VERSION = "1.0.0"
SANDBOX_ROOT_PREFIX = "HQE_MULTI_STRATEGY_PHASE4K_SANDBOX"


class LifecycleWriteSandboxError(ValueError):
    """Raised when a guarded sandbox write is unsafe or inconsistent."""


class SandboxTransitionStatus(str, Enum):
    APPLIED_SANDBOX = "APPLIED_SANDBOX"


@dataclass(frozen=True)
class GuardedLifecycleWritePermit:
    """Immutable permit scoped to one reviewed current-SMC sandbox namespace."""

    strategy_id: str
    strategy_version: str
    implementation_key: str
    selection_hash: str
    plan_hash: str
    sandbox_root: str
    namespace_directory: str
    schema_version: str = LIFECYCLE_WRITE_SANDBOX_SCHEMA_VERSION
    sandbox_write_authorized: bool = True
    canonical_selection_write_authorized: bool = False
    canonical_state_write_authorized: bool = False
    canonical_ledger_write_authorized: bool = False
    canonical_runtime_connected: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != LIFECYCLE_WRITE_SANDBOX_SCHEMA_VERSION:
            raise LifecycleWriteSandboxError("unsupported sandbox permit schema")
        if not self.sandbox_write_authorized:
            raise LifecycleWriteSandboxError("sandbox write permit must be authorized")
        if any(
            (
                self.canonical_selection_write_authorized,
                self.canonical_state_write_authorized,
                self.canonical_ledger_write_authorized,
                self.canonical_runtime_connected,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise LifecycleWriteSandboxError("sandbox permit cannot authorize canonical execution")

    @classmethod
    def issue(
        cls,
        *,
        plan: DisabledCanonicalLifecyclePlan,
        selection: StrategySelectionSnapshot,
        sandbox_root: str | Path,
    ) -> "GuardedLifecycleWritePermit":
        if plan.status is not DisabledLifecyclePlanStatus.READY_DISABLED:
            raise LifecycleWriteSandboxError("lifecycle plan is not READY_DISABLED")
        if plan.blockers:
            raise LifecycleWriteSandboxError("READY_DISABLED plan contains blockers")
        if plan.selection_hash != selection.selection_hash:
            raise LifecycleWriteSandboxError("plan does not match selected strategy")
        if plan.current_lifecycle is not PositionLifecycle.FLAT:
            raise LifecycleWriteSandboxError("sandbox permit requires FLAT lifecycle")
        if (
            selection.strategy_id != CURRENT_SMC_STRATEGY_ID
            or selection.strategy_version != CURRENT_SMC_STRATEGY_VERSION
            or selection.implementation_key != CURRENT_SMC_IMPLEMENTATION_KEY
        ):
            raise LifecycleWriteSandboxError("permit supports reviewed current SMC only")
        root = Path(sandbox_root).resolve(strict=False)
        if not root.name.startswith(SANDBOX_ROOT_PREFIX):
            raise LifecycleWriteSandboxError("sandbox root must use the Phase 4K prefix")
        canonical_namespace = Path(plan.namespace_directory).resolve(strict=False)
        if root == canonical_namespace or root in canonical_namespace.parents:
            raise LifecycleWriteSandboxError("sandbox root overlaps canonical namespace")
        namespace = StrategyArtifactPaths.from_selection(root, selection).namespace_directory
        return cls(
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            implementation_key=selection.implementation_key,
            selection_hash=selection.selection_hash,
            plan_hash=plan.plan_hash,
            sandbox_root=str(root),
            namespace_directory=str(namespace),
        )

    @property
    def permit_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "implementation_key": self.implementation_key,
            "selection_hash": self.selection_hash,
            "plan_hash": self.plan_hash,
            "sandbox_root": self.sandbox_root,
            "namespace_directory": self.namespace_directory,
            "sandbox_write_authorized": True,
            "canonical_selection_write_authorized": False,
            "canonical_state_write_authorized": False,
            "canonical_ledger_write_authorized": False,
            "canonical_runtime_connected": False,
            "runtime_cutover_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["permit_hash"] = self.permit_hash
        return payload


@dataclass(frozen=True)
class SandboxTransitionResult:
    status: SandboxTransitionStatus
    event_id: str
    transition: str
    event_hash: str
    bundle_hash: str
    namespace_directory: str
    sandbox_state_written: bool = True
    sandbox_ledger_written: bool = True
    canonical_state_written: bool = False
    canonical_ledger_written: bool = False
    canonical_runtime_connected: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_performed: bool = False
    real_money_used: bool = False

    def __post_init__(self) -> None:
        if self.status is not SandboxTransitionStatus.APPLIED_SANDBOX:
            raise LifecycleWriteSandboxError("invalid sandbox transition result")
        if not self.sandbox_state_written or not self.sandbox_ledger_written:
            raise LifecycleWriteSandboxError("sandbox projections must be written")
        if any(
            (
                self.canonical_state_written,
                self.canonical_ledger_written,
                self.canonical_runtime_connected,
                self.runtime_cutover_authorized,
                self.broker_execution_performed,
                self.real_money_used,
            )
        ):
            raise LifecycleWriteSandboxError("sandbox result cannot touch canonical execution")


class GuardedNamespacedLifecycleWriteSandbox:
    """Transactional process-level lifecycle sandbox for current reviewed SMC."""

    def __init__(
        self,
        *,
        permit: GuardedLifecycleWritePermit,
        selection: StrategySelectionSnapshot,
    ) -> None:
        if permit.selection_hash != selection.selection_hash:
            raise LifecycleWriteSandboxError("permit does not match selection")
        self.permit = permit
        self.selection = selection
        self.root = Path(permit.sandbox_root).resolve(strict=False)
        self.paths = StrategyArtifactPaths.from_selection(self.root, selection)
        if str(self.paths.namespace_directory) != permit.namespace_directory:
            raise LifecycleWriteSandboxError("permit namespace mismatch")
        self.bundle_path = self.paths.namespace_directory / "lifecycle_bundle.json"
        self.lock_path = self.paths.namespace_directory / ".phase4k_write.lock"

    def initialize(self, initial_state: StrategyStateSnapshot) -> SandboxLifecycleBundle:
        if not initial_state.matches_selection(self.selection):
            raise LifecycleWriteSandboxError("initial state does not match selection")
        if initial_state.lifecycle is not PositionLifecycle.FLAT:
            raise LifecycleWriteSandboxError("sandbox initialization requires FLAT state")
        if not initial_state.migration_complete:
            raise LifecycleWriteSandboxError("sandbox initialization requires migrated state")
        if self.bundle_path.exists():
            existing = read_bundle(self.bundle_path)
            if existing.selection.selection_hash != self.selection.selection_hash:
                raise LifecycleWriteSandboxError("existing sandbox belongs to another selection")
            return existing
        bundle = SandboxLifecycleBundle(
            selection=self.selection,
            current_state=initial_state,
        )
        self._write_transaction(bundle, previous=None)
        return bundle

    def load(self) -> SandboxLifecycleBundle:
        bundle = read_bundle(self.bundle_path)
        if bundle.selection.selection_hash != self.selection.selection_hash:
            raise LifecycleWriteSandboxError("sandbox bundle selection mismatch")
        return bundle

    def apply_transition(
        self,
        *,
        before: StrategyStateSnapshot,
        after: StrategyStateSnapshot,
        event_id: str,
        event_time: str,
        option_side: str,
        option_symbol: str = "",
        quantity: int = 0,
        price: float | None = None,
        realized_pnl: float | None = None,
        reason_code: str = "",
    ) -> SandboxTransitionResult:
        lock_handle = self._acquire_lock()
        try:
            current = self.load()
            current_hash = state_hash(current.current_state)
            if current_hash != state_hash(before):
                raise LifecycleWriteSandboxError("stale before-state snapshot")
            if any(item.event_id == event_id for item in current.events):
                raise LifecycleWriteSandboxError("duplicate lifecycle event_id")
            if after.last_event_id != event_id:
                raise LifecycleWriteSandboxError("after-state last_event_id must equal event_id")
            projection = DisabledCanonicalLifecycleAdapter().project_transition(
                selection=self.selection,
                before=before,
                after=after,
            )
            if not projection.allowed:
                raise LifecycleWriteSandboxError("; ".join(projection.blockers))
            previous_event_hash = current.events[-1].event_hash if current.events else ""
            event = SandboxLifecycleEvent(
                event_id=str(event_id),
                event_time=str(event_time),
                strategy_id=self.selection.strategy_id,
                strategy_version=self.selection.strategy_version,
                selection_hash=self.selection.selection_hash,
                before_state_hash=current_hash,
                after_state=after.to_dict(),
                transition=projection.transition,
                option_side=str(option_side),
                option_symbol=str(option_symbol),
                quantity=quantity,
                price=price,
                realized_pnl=realized_pnl,
                reason_code=str(reason_code),
                previous_event_hash=previous_event_hash,
            )
            updated = SandboxLifecycleBundle(
                selection=self.selection,
                current_state=after,
                events=current.events + (event,),
            )
            self._write_transaction(updated, previous=current)
            return SandboxTransitionResult(
                status=SandboxTransitionStatus.APPLIED_SANDBOX,
                event_id=event.event_id,
                transition=event.transition,
                event_hash=event.event_hash,
                bundle_hash=updated.bundle_hash,
                namespace_directory=str(self.paths.namespace_directory),
            )
        finally:
            self._release_lock(lock_handle)

    def repair_projections(self) -> SandboxLifecycleBundle:
        bundle = self.load()
        self._write_projection_files(bundle)
        return bundle

    def _acquire_lock(self):
        self.paths.namespace_directory.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise LifecycleWriteSandboxError("sandbox lifecycle write lock is active") from exc
        handle = os.fdopen(descriptor, "w", encoding="utf-8")
        handle.write(str(os.getpid()))
        handle.flush()
        return handle

    def _release_lock(self, handle) -> None:
        try:
            handle.close()
        finally:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _write_transaction(
        self,
        bundle: SandboxLifecycleBundle,
        *,
        previous: SandboxLifecycleBundle | None,
    ) -> None:
        old_bundle = self.bundle_path.read_bytes() if self.bundle_path.exists() else None
        old_selection = self.paths.selection.read_bytes() if self.paths.selection.exists() else None
        old_state = self.paths.state.read_bytes() if self.paths.state.exists() else None
        old_ledger = self.paths.ledger.read_bytes() if self.paths.ledger.exists() else None
        try:
            write_bundle_atomic(self.bundle_path, bundle)
            self._write_projection_files(bundle)
        except Exception as exc:
            self._restore_file(self.bundle_path, old_bundle)
            self._restore_file(self.paths.selection, old_selection)
            self._restore_file(self.paths.state, old_state)
            self._restore_file(self.paths.ledger, old_ledger)
            if isinstance(exc, (LifecycleWriteSandboxError, LifecycleJournalError)):
                raise
            raise LifecycleWriteSandboxError("sandbox transaction rolled back") from exc
        if previous is not None and read_bundle(self.bundle_path).bundle_hash != bundle.bundle_hash:
            raise LifecycleWriteSandboxError("sandbox transaction verification failed")

    def _write_projection_files(self, bundle: SandboxLifecycleBundle) -> None:
        self.paths.namespace_directory.mkdir(parents=True, exist_ok=True)
        self._atomic_text(
            self.paths.selection,
            json.dumps(bundle.selection.to_dict(), indent=2, sort_keys=True) + "\n",
        )
        self._atomic_text(
            self.paths.state,
            json.dumps(bundle.current_state.to_dict(), indent=2, sort_keys=True) + "\n",
        )
        rows = []
        for event in bundle.events:
            after = StrategyStateSnapshot.from_dict(event.after_state)
            rows.append(
                {
                    "ledger_schema_version": "1.0.0",
                    "event_id": event.event_id,
                    "event_time": event.event_time,
                    "strategy_id": event.strategy_id,
                    "strategy_version": event.strategy_version,
                    "selection_hash": event.selection_hash,
                    "parameters_hash": after.parameters_hash,
                    "lifecycle": after.lifecycle.value,
                    "option_side": event.option_side,
                    "option_symbol": event.option_symbol,
                    "quantity": str(event.quantity),
                    "price": "" if event.price is None else str(event.price),
                    "realized_pnl": (
                        "" if event.realized_pnl is None else str(event.realized_pnl)
                    ),
                    "reason_code": event.reason_code,
                }
            )
        temporary = self.paths.ledger.with_name(self.paths.ledger.name + f".{os.getpid()}.tmp")
        try:
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(LEDGER_COLUMNS),
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temporary, self.paths.ledger)
        except (OSError, csv.Error) as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise LifecycleWriteSandboxError("unable to write sandbox ledger projection") from exc

    @staticmethod
    def _atomic_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8", newline="\n")
            os.replace(temporary, path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise LifecycleWriteSandboxError(f"unable to write sandbox projection: {path}") from exc

    @staticmethod
    def _restore_file(path: Path, data: bytes | None) -> None:
        if data is None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + f".rollback.{os.getpid()}.tmp")
        temporary.write_bytes(data)
        os.replace(temporary, path)
