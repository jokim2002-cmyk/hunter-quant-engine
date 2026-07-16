"""Disabled activation preflight for HQE multi-strategy evidence.

This module evaluates whether offline evidence is internally ready for a later
review. It never authorizes strategy activation, runtime connection, lifecycle
writes, broker execution, or cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.multi_strategy.errors import ActivationPreflightError
from src.multi_strategy.evidence_view import OperatorEvidenceView
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.manifest import CANONICAL_OPTION_MAPPING, StrategyManifest
from src.multi_strategy.recovery import (
    OfflineRecoveryReadiness,
    OfflineRestartRecoverySnapshot,
)
from src.multi_strategy.runtime_hook import StableRuntimeObservation
from src.multi_strategy.selection import (
    SelectionActivationStatus,
    StrategySelectionSnapshot,
)
from src.multi_strategy.session import ShadowSessionStatus

ACTIVATION_PREFLIGHT_SCHEMA_VERSION = "1.0.0"


class ActivationPreflightStatus(str, Enum):
    """Readiness classification while activation remains impossible."""

    READY_DISABLED = "READY_DISABLED"
    BLOCKED_RUNTIME_ACTIVE = "BLOCKED_RUNTIME_ACTIVE"
    BLOCKED_EVIDENCE = "BLOCKED_EVIDENCE"


@dataclass(frozen=True)
class DisabledActivationPreflightResult:
    """Immutable evidence result with activation permanently disabled."""

    status: ActivationPreflightStatus
    strategy_id: str
    strategy_version: str
    selection_hash: str
    recovery_snapshot_hash: str
    operator_view_hash: str
    runtime_observation_hash: str
    blockers: tuple[str, ...]
    minimum_cycles: int
    observed_cycles: int
    match_count: int
    mismatch_count: int
    schema_version: str = ACTIVATION_PREFLIGHT_SCHEMA_VERSION
    activation_authorized: bool = False
    runtime_connection_authorized: bool = False
    runtime_cutover_authorized: bool = False
    lifecycle_write_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != ACTIVATION_PREFLIGHT_SCHEMA_VERSION:
            raise ActivationPreflightError(
                "unsupported activation preflight schema version"
            )
        if self.minimum_cycles < 1:
            raise ActivationPreflightError("minimum_cycles must be positive")
        if self.observed_cycles < 0:
            raise ActivationPreflightError("observed_cycles cannot be negative")
        if self.match_count < 0 or self.mismatch_count < 0:
            raise ActivationPreflightError("parity counts cannot be negative")
        if self.observed_cycles != self.match_count + self.mismatch_count:
            raise ActivationPreflightError(
                "observed_cycles must equal match plus mismatch counts"
            )
        if any(
            (
                self.activation_authorized,
                self.runtime_connection_authorized,
                self.runtime_cutover_authorized,
                self.lifecycle_write_authorized,
                self.state_write_authorized,
                self.ledger_write_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise ActivationPreflightError(
                "disabled preflight cannot authorize activation or execution"
            )
        if self.status is ActivationPreflightStatus.READY_DISABLED:
            if self.blockers:
                raise ActivationPreflightError(
                    "READY_DISABLED preflight cannot contain blockers"
                )
        elif not self.blockers:
            raise ActivationPreflightError(
                "blocked preflight must contain at least one blocker"
            )

    @property
    def preflight_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "recovery_snapshot_hash": self.recovery_snapshot_hash,
            "operator_view_hash": self.operator_view_hash,
            "runtime_observation_hash": self.runtime_observation_hash,
            "blockers": list(self.blockers),
            "minimum_cycles": self.minimum_cycles,
            "observed_cycles": self.observed_cycles,
            "match_count": self.match_count,
            "mismatch_count": self.mismatch_count,
            "activation_authorized": False,
            "runtime_connection_authorized": False,
            "runtime_cutover_authorized": False,
            "lifecycle_write_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["preflight_hash"] = self.preflight_hash
        return payload


class DisabledActivationPreflight:
    """Evaluate immutable evidence without providing an activation API."""

    def __init__(self, *, minimum_cycles: int = 3) -> None:
        if not isinstance(minimum_cycles, int) or minimum_cycles < 1:
            raise ActivationPreflightError(
                "minimum_cycles must be a positive integer"
            )
        self.minimum_cycles = minimum_cycles

    def evaluate(
        self,
        *,
        manifest: StrategyManifest,
        selection: StrategySelectionSnapshot,
        recovery: OfflineRestartRecoverySnapshot,
        operator_view: OperatorEvidenceView,
        runtime_observation: StableRuntimeObservation,
    ) -> DisabledActivationPreflightResult:
        manifest.require_valid()
        self._validate_identity(
            manifest=manifest,
            selection=selection,
            recovery=recovery,
            operator_view=operator_view,
        )

        blockers: list[str] = []
        if operator_view.status is not ShadowSessionStatus.CLOSED:
            blockers.append("shadow session is not CLOSED")
        if operator_view.overall_status != "PASS_CLOSED":
            blockers.append("operator evidence is not PASS_CLOSED")
        if operator_view.mismatch_count:
            blockers.append("operator evidence contains parity mismatches")
        if operator_view.cycle_count < self.minimum_cycles:
            blockers.append(
                f"requires at least {self.minimum_cycles} parity cycles"
            )
        if operator_view.match_count != operator_view.cycle_count:
            blockers.append("not every parity cycle is a MATCH")

        required_signals = {"LONG", "SHORT", "NEUTRAL"}
        if not required_signals.issubset(
            {key for key, value in operator_view.signal_counts.items() if value > 0}
        ):
            blockers.append("LONG/SHORT/NEUTRAL coverage is incomplete")

        required_sides = set(CANONICAL_OPTION_MAPPING.values())
        if not required_sides.issubset(
            {
                key
                for key, value in operator_view.option_side_counts.items()
                if value > 0
            }
        ):
            blockers.append("CE_BUY/PE_BUY/NO_TRADE coverage is incomplete")

        if runtime_observation.runtime_status not in {"STOPPED", "NOT_FOUND"}:
            blockers.append(
                "canonical runtime must be STOPPED or NOT_FOUND for later review"
            )
            status = ActivationPreflightStatus.BLOCKED_RUNTIME_ACTIVE
        elif blockers:
            status = ActivationPreflightStatus.BLOCKED_EVIDENCE
        else:
            status = ActivationPreflightStatus.READY_DISABLED

        return DisabledActivationPreflightResult(
            status=status,
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            selection_hash=selection.selection_hash,
            recovery_snapshot_hash=recovery.snapshot_hash,
            operator_view_hash=operator_view.view_hash,
            runtime_observation_hash=runtime_observation.observation_hash,
            blockers=tuple(blockers),
            minimum_cycles=self.minimum_cycles,
            observed_cycles=operator_view.cycle_count,
            match_count=operator_view.match_count,
            mismatch_count=operator_view.mismatch_count,
        )

    @staticmethod
    def _validate_identity(
        *,
        manifest: StrategyManifest,
        selection: StrategySelectionSnapshot,
        recovery: OfflineRestartRecoverySnapshot,
        operator_view: OperatorEvidenceView,
    ) -> None:
        issues: list[str] = []
        if selection.activation_status is not SelectionActivationStatus.DISABLED:
            issues.append("selection activation must remain DISABLED")
        if selection.runtime_connected:
            issues.append("selection cannot be runtime-connected")
        if recovery.readiness is not OfflineRecoveryReadiness.READY_FLAT:
            issues.append("recovery must be READY_FLAT")
        if recovery.runtime_connected or recovery.runtime_cutover_performed:
            issues.append("recovery must remain offline without cutover")
        if manifest.strategy_id != selection.strategy_id:
            issues.append("manifest strategy_id does not match selection")
        if manifest.strategy_version != selection.strategy_version:
            issues.append("manifest strategy_version does not match selection")
        if manifest.implementation_key != selection.implementation_key:
            issues.append("manifest implementation_key does not match selection")
        if manifest.fingerprint() != selection.manifest_fingerprint:
            issues.append("manifest fingerprint does not match selection")
        if recovery.selection.selection_hash != selection.selection_hash:
            issues.append("recovery selection hash does not match selection")
        if operator_view.selection_hash != selection.selection_hash:
            issues.append("operator selection hash does not match selection")
        if operator_view.recovery_snapshot_hash != recovery.snapshot_hash:
            issues.append("operator recovery hash does not match recovery")
        if any(
            (
                operator_view.runtime_connected,
                operator_view.runtime_cutover_performed,
                operator_view.state_written,
                operator_view.ledger_written,
                operator_view.broker_execution_performed,
            )
        ):
            issues.append("operator evidence contains forbidden lifecycle flags")
        if issues:
            raise ActivationPreflightError("; ".join(issues))
