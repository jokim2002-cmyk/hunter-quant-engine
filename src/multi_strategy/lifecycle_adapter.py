"""Disabled canonical lifecycle integration adapter for HQE.

The adapter validates one selected reviewed strategy against existing offline
recovery, parity/preflight, runtime observation, and namespaced state evidence.
It projects canonical FLAT/OPEN/HELD/CLOSED transitions but never writes state,
ledger, selection, or runtime files and never authorizes activation or cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.multi_strategy.activation import (
    ActivationPreflightStatus,
    DisabledActivationPreflightResult,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.manifest import StrategyManifest
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.recovery import (
    OfflineRecoveryReadiness,
    OfflineRestartRecoverySnapshot,
)
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle, StrategyStateSnapshot

LIFECYCLE_ADAPTER_SCHEMA_VERSION = "1.0.0"
CANONICAL_LIFECYCLE_STAGES = (
    PositionLifecycle.FLAT,
    PositionLifecycle.OPEN,
    PositionLifecycle.HELD,
    PositionLifecycle.CLOSED,
)
_ALLOWED_TRANSITIONS = {
    (PositionLifecycle.FLAT, PositionLifecycle.FLAT),
    (PositionLifecycle.FLAT, PositionLifecycle.OPEN),
    (PositionLifecycle.OPEN, PositionLifecycle.OPEN),
    (PositionLifecycle.OPEN, PositionLifecycle.HELD),
    (PositionLifecycle.OPEN, PositionLifecycle.CLOSED),
    (PositionLifecycle.HELD, PositionLifecycle.HELD),
    (PositionLifecycle.HELD, PositionLifecycle.CLOSED),
    (PositionLifecycle.CLOSED, PositionLifecycle.CLOSED),
    (PositionLifecycle.CLOSED, PositionLifecycle.FLAT),
}


class LifecycleAdapterError(ValueError):
    """Raised when disabled lifecycle integration evidence is inconsistent."""


class DisabledLifecyclePlanStatus(str, Enum):
    """Preparation status while activation and cutover remain disabled."""

    READY_DISABLED = "READY_DISABLED"
    BLOCKED_RUNTIME_ACTIVE = "BLOCKED_RUNTIME_ACTIVE"
    BLOCKED_OPEN_POSITION = "BLOCKED_OPEN_POSITION"
    BLOCKED_EVIDENCE = "BLOCKED_EVIDENCE"


@dataclass(frozen=True)
class DisabledLifecycleTransitionProjection:
    """Read-only projection of one canonical lifecycle transition."""

    strategy_id: str
    strategy_version: str
    selection_hash: str
    before_lifecycle: PositionLifecycle
    after_lifecycle: PositionLifecycle
    before_state_hash: str
    after_state_hash: str
    allowed: bool
    blockers: tuple[str, ...]
    schema_version: str = LIFECYCLE_ADAPTER_SCHEMA_VERSION
    lifecycle_write_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    runtime_connected: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != LIFECYCLE_ADAPTER_SCHEMA_VERSION:
            raise LifecycleAdapterError(
                "unsupported lifecycle projection schema version"
            )
        if any(
            (
                self.lifecycle_write_authorized,
                self.state_write_authorized,
                self.ledger_write_authorized,
                self.runtime_connected,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise LifecycleAdapterError(
                "disabled transition projection cannot authorize writes or execution"
            )
        if self.allowed and self.blockers:
            raise LifecycleAdapterError(
                "allowed transition cannot contain blockers"
            )
        if not self.allowed and not self.blockers:
            raise LifecycleAdapterError(
                "blocked transition requires blockers"
            )

    @property
    def transition(self) -> str:
        return f"{self.before_lifecycle.value}->{self.after_lifecycle.value}"

    @property
    def projection_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "before_lifecycle": self.before_lifecycle.value,
            "after_lifecycle": self.after_lifecycle.value,
            "transition": self.transition,
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "allowed": self.allowed,
            "blockers": list(self.blockers),
            "lifecycle_write_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "runtime_connected": False,
            "runtime_cutover_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["projection_hash"] = self.projection_hash
        return payload


@dataclass(frozen=True)
class DisabledCanonicalLifecyclePlan:
    """Immutable one-active integration plan with every control disabled."""

    status: DisabledLifecyclePlanStatus
    strategy_id: str
    strategy_version: str
    implementation_key: str
    manifest_fingerprint: str
    selection_hash: str
    one_active_set_hash: str
    current_state_hash: str
    recovery_snapshot_hash: str
    preflight_hash: str
    runtime_observation_hash: str
    namespace_directory: str
    current_lifecycle: PositionLifecycle
    blockers: tuple[str, ...]
    schema_version: str = LIFECYCLE_ADAPTER_SCHEMA_VERSION
    active_strategy_count: int = 1
    one_active_strategy_enforced: bool = True
    activation_authorized: bool = False
    selection_write_authorized: bool = False
    lifecycle_write_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    runtime_control_authorized: bool = False
    runtime_connected: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != LIFECYCLE_ADAPTER_SCHEMA_VERSION:
            raise LifecycleAdapterError(
                "unsupported lifecycle plan schema version"
            )
        if self.active_strategy_count != 1:
            raise LifecycleAdapterError(
                "lifecycle plan requires exactly one active strategy"
            )
        if not self.one_active_strategy_enforced:
            raise LifecycleAdapterError(
                "one-active strategy enforcement must remain enabled"
            )
        if any(
            (
                self.activation_authorized,
                self.selection_write_authorized,
                self.lifecycle_write_authorized,
                self.state_write_authorized,
                self.ledger_write_authorized,
                self.runtime_control_authorized,
                self.runtime_connected,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise LifecycleAdapterError(
                "disabled lifecycle plan cannot authorize activation, writes, or execution"
            )
        if self.status is DisabledLifecyclePlanStatus.READY_DISABLED:
            if self.blockers:
                raise LifecycleAdapterError(
                    "READY_DISABLED plan cannot contain blockers"
                )
        elif not self.blockers:
            raise LifecycleAdapterError(
                "blocked lifecycle plan requires blockers"
            )

    @property
    def plan_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "implementation_key": self.implementation_key,
            "manifest_fingerprint": self.manifest_fingerprint,
            "selection_hash": self.selection_hash,
            "one_active_set_hash": self.one_active_set_hash,
            "current_state_hash": self.current_state_hash,
            "recovery_snapshot_hash": self.recovery_snapshot_hash,
            "preflight_hash": self.preflight_hash,
            "runtime_observation_hash": self.runtime_observation_hash,
            "namespace_directory": self.namespace_directory,
            "current_lifecycle": self.current_lifecycle.value,
            "canonical_lifecycle_stages": [
                stage.value for stage in CANONICAL_LIFECYCLE_STAGES
            ],
            "blockers": list(self.blockers),
            "active_strategy_count": 1,
            "one_active_strategy_enforced": True,
            "activation_authorized": False,
            "selection_write_authorized": False,
            "lifecycle_write_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "runtime_control_authorized": False,
            "runtime_connected": False,
            "runtime_cutover_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["plan_hash"] = self.plan_hash
        return payload


class DisabledCanonicalLifecycleAdapter:
    """Prepare and project lifecycle integration without applying it."""

    @staticmethod
    def _validate_identity(
        *,
        manifest: StrategyManifest,
        selection: StrategySelectionSnapshot,
        one_active: DisabledOneActiveStrategySet,
        current_state: StrategyStateSnapshot,
        recovery: OfflineRestartRecoverySnapshot,
        preflight: DisabledActivationPreflightResult,
        runtime_observation: StableRuntimeObservation,
    ) -> None:
        issues: list[str] = []
        if manifest.strategy_id != selection.strategy_id:
            issues.append("manifest strategy_id does not match selection")
        if manifest.strategy_version != selection.strategy_version:
            issues.append("manifest strategy_version does not match selection")
        if manifest.implementation_key != selection.implementation_key:
            issues.append("manifest implementation_key does not match selection")
        if manifest.fingerprint() != selection.manifest_fingerprint:
            issues.append("manifest fingerprint does not match selection")
        if one_active.selection.selection_hash != selection.selection_hash:
            issues.append("one-active set does not match selection")
        if not current_state.matches_selection(selection):
            issues.append("current state does not match selection")
        if recovery.selection.selection_hash != selection.selection_hash:
            issues.append("recovery selection does not match selection")
        if recovery.readiness is not OfflineRecoveryReadiness.READY_FLAT:
            issues.append("recovery is not READY_FLAT")
        if preflight.strategy_id != selection.strategy_id:
            issues.append("preflight strategy_id does not match selection")
        if preflight.strategy_version != selection.strategy_version:
            issues.append("preflight strategy_version does not match selection")
        if preflight.selection_hash != selection.selection_hash:
            issues.append("preflight selection_hash does not match selection")
        if preflight.recovery_snapshot_hash != recovery.snapshot_hash:
            issues.append("preflight recovery hash does not match recovery")
        if (
            preflight.runtime_observation_hash
            != runtime_observation.observation_hash
        ):
            issues.append("preflight runtime observation does not match")
        if issues:
            raise LifecycleAdapterError("; ".join(issues))

    def prepare(
        self,
        *,
        manifest: StrategyManifest,
        selection: StrategySelectionSnapshot,
        one_active: DisabledOneActiveStrategySet,
        current_state: StrategyStateSnapshot,
        recovery: OfflineRestartRecoverySnapshot,
        preflight: DisabledActivationPreflightResult,
        runtime_observation: StableRuntimeObservation,
    ) -> DisabledCanonicalLifecyclePlan:
        manifest.require_valid()
        self._validate_identity(
            manifest=manifest,
            selection=selection,
            one_active=one_active,
            current_state=current_state,
            recovery=recovery,
            preflight=preflight,
            runtime_observation=runtime_observation,
        )

        blockers: list[str] = []
        if not current_state.migration_complete:
            blockers.append("current strategy state migration is incomplete")
        if current_state.lifecycle.has_open_position:
            blockers.append(
                "canonical lifecycle has an OPEN or HELD position"
            )
        if preflight.status is not ActivationPreflightStatus.READY_DISABLED:
            blockers.append("disabled activation preflight is not READY_DISABLED")
        if runtime_observation.runtime_status not in {"STOPPED", "NOT_FOUND"}:
            blockers.append("canonical runtime must be STOPPED or NOT_FOUND")

        if runtime_observation.runtime_status not in {"STOPPED", "NOT_FOUND"}:
            status = DisabledLifecyclePlanStatus.BLOCKED_RUNTIME_ACTIVE
        elif current_state.lifecycle.has_open_position:
            status = DisabledLifecyclePlanStatus.BLOCKED_OPEN_POSITION
        elif blockers:
            status = DisabledLifecyclePlanStatus.BLOCKED_EVIDENCE
        else:
            status = DisabledLifecyclePlanStatus.READY_DISABLED

        return DisabledCanonicalLifecyclePlan(
            status=status,
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            implementation_key=selection.implementation_key,
            manifest_fingerprint=selection.manifest_fingerprint,
            selection_hash=selection.selection_hash,
            one_active_set_hash=one_active.set_hash,
            current_state_hash=canonical_mapping_hash(current_state.to_dict()),
            recovery_snapshot_hash=recovery.snapshot_hash,
            preflight_hash=preflight.preflight_hash,
            runtime_observation_hash=runtime_observation.observation_hash,
            namespace_directory=recovery.namespace_directory,
            current_lifecycle=current_state.lifecycle,
            blockers=tuple(blockers),
        )

    def project_transition(
        self,
        *,
        selection: StrategySelectionSnapshot,
        before: StrategyStateSnapshot,
        after: StrategyStateSnapshot,
    ) -> DisabledLifecycleTransitionProjection:
        if not before.matches_selection(selection):
            raise LifecycleAdapterError(
                "before state does not match selected strategy"
            )
        if not after.matches_selection(selection):
            raise LifecycleAdapterError(
                "after state does not match selected strategy"
            )

        blockers: list[str] = []
        transition = (before.lifecycle, after.lifecycle)
        if transition not in _ALLOWED_TRANSITIONS:
            blockers.append(
                "unsupported canonical lifecycle transition "
                f"{before.lifecycle.value}->{after.lifecycle.value}"
            )
        if not before.migration_complete or not after.migration_complete:
            blockers.append("lifecycle projection requires migrated state")

        if before.lifecycle.has_open_position and after.lifecycle.has_open_position:
            for field in ("option_symbol", "option_side"):
                before_value = str(before.position.get(field, ""))
                after_value = str(after.position.get(field, ""))
                if before_value != after_value:
                    blockers.append(
                        f"open position {field} cannot change during lifecycle projection"
                    )

        return DisabledLifecycleTransitionProjection(
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            selection_hash=selection.selection_hash,
            before_lifecycle=before.lifecycle,
            after_lifecycle=after.lifecycle,
            before_state_hash=canonical_mapping_hash(before.to_dict()),
            after_state_hash=canonical_mapping_hash(after.to_dict()),
            allowed=not blockers,
            blockers=tuple(blockers),
        )
