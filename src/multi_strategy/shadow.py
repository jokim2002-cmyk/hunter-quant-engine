"""Offline shadow-decision parity for the current registered SMC strategy."""

from __future__ import annotations

import copy
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from scripts import hqe_smc_live_direction as legacy_smc

from src.multi_strategy.adapters.current_smc import (
    CurrentSmcCompatibilityAdapter,
)
from src.multi_strategy.errors import ShadowParityError
from src.multi_strategy.execution import (
    ExecutionMode,
    canonical_mapping_hash,
)
from src.multi_strategy.recorded import (
    RecordedStrategyEvaluationResult,
    RecordedStrategyInput,
    RegisteredRecordedEvaluator,
)
from src.multi_strategy.recovery import (
    OfflineRecoveryReadiness,
    OfflineRestartRecoverySnapshot,
)
from src.multi_strategy.registry import StrategyRegistry
from src.multi_strategy.selection import (
    SelectionActivationStatus,
    StrategySelectionSnapshot,
)
from src.multi_strategy.storage import PositionLifecycle

SHADOW_PARITY_SCHEMA_VERSION = "1.0.0"


class ShadowParityStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"


@dataclass(frozen=True)
class ShadowParityResult:
    """One deterministic comparison with no runtime or state writes."""

    status: ShadowParityStatus
    selection_hash: str
    recovery_snapshot_hash: str
    input_identity: str
    execution_mode: ExecutionMode
    legacy_payload: Mapping[str, Any]
    registered_result: RecordedStrategyEvaluationResult
    mismatch_reasons: tuple[str, ...]
    schema_version: str = SHADOW_PARITY_SCHEMA_VERSION
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    state_written: bool = False
    ledger_written: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != SHADOW_PARITY_SCHEMA_VERSION:
            raise ShadowParityError(
                "unsupported shadow parity schema version"
            )
        if self.runtime_connected or self.runtime_cutover_performed:
            raise ShadowParityError(
                "shadow parity cannot connect or cut over runtime"
            )
        if self.state_written or self.ledger_written:
            raise ShadowParityError(
                "shadow parity cannot write state or ledger"
            )
        if (
            self.status is ShadowParityStatus.MATCH
            and self.mismatch_reasons
        ):
            raise ShadowParityError(
                "MATCH result cannot contain mismatch reasons"
            )
        if (
            self.status is ShadowParityStatus.MISMATCH
            and not self.mismatch_reasons
        ):
            raise ShadowParityError(
                "MISMATCH result requires mismatch reasons"
            )
        object.__setattr__(
            self,
            "legacy_payload",
            copy.deepcopy(dict(self.legacy_payload)),
        )

    @property
    def result_hash(self) -> str:
        return canonical_mapping_hash(
            {
                "schema_version": self.schema_version,
                "status": self.status.value,
                "selection_hash": self.selection_hash,
                "recovery_snapshot_hash": self.recovery_snapshot_hash,
                "input_identity": self.input_identity,
                "execution_mode": self.execution_mode.value,
                "legacy_payload": dict(self.legacy_payload),
                "registered_result": self.registered_result.to_dict(),
                "mismatch_reasons": list(self.mismatch_reasons),
                "runtime_connected": self.runtime_connected,
                "runtime_cutover_performed": (
                    self.runtime_cutover_performed
                ),
                "state_written": self.state_written,
                "ledger_written": self.ledger_written,
            }
        )

    def require_match(self) -> "ShadowParityResult":
        if self.status is not ShadowParityStatus.MATCH:
            raise ShadowParityError(
                "shadow decision parity failed: "
                + "; ".join(self.mismatch_reasons)
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "selection_hash": self.selection_hash,
            "recovery_snapshot_hash": self.recovery_snapshot_hash,
            "input_identity": self.input_identity,
            "execution_mode": self.execution_mode.value,
            "legacy_payload": copy.deepcopy(dict(self.legacy_payload)),
            "registered_result": self.registered_result.to_dict(),
            "mismatch_reasons": list(self.mismatch_reasons),
            "runtime_connected": self.runtime_connected,
            "runtime_cutover_performed": (
                self.runtime_cutover_performed
            ),
            "state_written": self.state_written,
            "ledger_written": self.ledger_written,
            "result_hash": self.result_hash,
        }


class OfflineShadowParityRunner:
    """Compare direct legacy and registered decisions without lifecycle writes."""

    def __init__(
        self,
        *,
        registry: StrategyRegistry,
        selection: StrategySelectionSnapshot,
        recovery: OfflineRestartRecoverySnapshot,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise ShadowParityError(
                "offline shadow runner cannot connect to runtime"
            )
        if selection.activation_status is not (
            SelectionActivationStatus.DISABLED
        ):
            raise ShadowParityError(
                "shadow selection must remain DISABLED"
            )
        if selection.runtime_connected:
            raise ShadowParityError(
                "shadow selection cannot be runtime-connected"
            )
        if recovery.readiness is not OfflineRecoveryReadiness.READY_FLAT:
            raise ShadowParityError(
                "shadow runner requires READY_FLAT recovery evidence"
            )
        if recovery.selection.selection_hash != selection.selection_hash:
            raise ShadowParityError(
                "recovery snapshot does not match shadow selection"
            )
        if recovery.state.lifecycle is not PositionLifecycle.FLAT:
            raise ShadowParityError(
                "shadow runner requires FLAT recovery state"
            )
        if not recovery.state.migration_complete:
            raise ShadowParityError(
                "shadow runner requires completed migration evidence"
            )

        registration = registry.get(
            selection.strategy_id,
            selection.strategy_version,
        )
        manifest = registration.manifest
        if manifest.implementation_key != selection.implementation_key:
            raise ShadowParityError(
                "registry implementation key does not match selection"
            )
        if manifest.fingerprint() != selection.manifest_fingerprint:
            raise ShadowParityError(
                "registry manifest fingerprint does not match selection"
            )
        normalized = manifest.validate_parameters(selection.parameters)
        implementation = registry.create(
            selection.strategy_id,
            selection.strategy_version,
            parameters=normalized,
        )
        if not isinstance(implementation, CurrentSmcCompatibilityAdapter):
            raise ShadowParityError(
                "Phase 4D shadow runner supports current SMC adapter only"
            )
        if implementation.parameters_hash != selection.parameters_hash:
            raise ShadowParityError(
                "selection parameters_hash does not match implementation"
            )

        self._registry = registry
        self._selection = selection
        self._recovery = recovery
        self._implementation = implementation
        self.runtime_connected = False

    def run(
        self,
        request: RecordedStrategyInput,
    ) -> ShadowParityResult:
        """Run a deterministic FORWARD_PAPER shadow comparison offline."""

        with tempfile.TemporaryDirectory(
            prefix="hqe_multi_strategy_shadow_"
        ) as temporary_directory:
            index_csv, premium_csv = request.materialize_csv(
                temporary_directory
            )
            legacy_first = legacy_smc.evaluate_from_csv(
                index_csv,
                premium_csv,
                self._implementation.candidate,
                request.er20,
            )
            legacy_second = legacy_smc.evaluate_from_csv(
                index_csv,
                premium_csv,
                self._implementation.candidate,
                request.er20,
            )

        evaluator = RegisteredRecordedEvaluator(
            registry=self._registry,
            strategy_id=self._selection.strategy_id,
            strategy_version=self._selection.strategy_version,
            parameters=self._selection.parameters,
        )
        registered_first = evaluator.evaluate(
            request,
            execution_mode=ExecutionMode.FORWARD_PAPER,
        )
        registered_second = evaluator.evaluate(
            request,
            execution_mode=ExecutionMode.FORWARD_PAPER,
        )

        mismatches: list[str] = []
        if legacy_first != legacy_second:
            mismatches.append("legacy decision is not deterministic")
        if registered_first.to_dict() != registered_second.to_dict():
            mismatches.append("registered decision is not deterministic")
        if (
            registered_first.decision.to_legacy_payload()
            != legacy_first
        ):
            mismatches.append(
                "registered legacy payload differs from direct legacy output"
            )
        if registered_first.metadata.execution_mode is not (
            ExecutionMode.FORWARD_PAPER
        ):
            mismatches.append(
                "registered metadata execution mode is not FORWARD_PAPER"
            )
        if registered_first.input_identity != request.input_identity:
            mismatches.append("registered input identity mismatch")
        if registered_first.metadata.data_identity != request.input_identity:
            mismatches.append("registered metadata data identity mismatch")
        if registered_first.metadata.strategy_id != (
            self._selection.strategy_id
        ):
            mismatches.append("registered strategy_id mismatch")
        if registered_first.metadata.strategy_version != (
            self._selection.strategy_version
        ):
            mismatches.append("registered strategy_version mismatch")
        if registered_first.metadata.parameters_hash != (
            self._selection.parameters_hash
        ):
            mismatches.append("registered parameters_hash mismatch")
        if registered_first.decision.parameters_hash != (
            self._selection.parameters_hash
        ):
            mismatches.append("decision parameters_hash mismatch")

        status = (
            ShadowParityStatus.MATCH
            if not mismatches
            else ShadowParityStatus.MISMATCH
        )
        return ShadowParityResult(
            status=status,
            selection_hash=self._selection.selection_hash,
            recovery_snapshot_hash=self._recovery.snapshot_hash,
            input_identity=request.input_identity,
            execution_mode=ExecutionMode.FORWARD_PAPER,
            legacy_payload=legacy_first,
            registered_result=registered_first,
            mismatch_reasons=tuple(mismatches),
        )
