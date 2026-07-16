"""Read-only product/runtime observation hook for offline HQE shadow sessions.

The hook accepts a stable double-read observation supplied by an external
observer. It never starts, stops, controls, or writes the canonical runtime.
The only permitted write is the existing append-only parity evidence journal
managed by :mod:`src.multi_strategy.session` outside the strategy namespace.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from src.multi_strategy.errors import RuntimeShadowHookError
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.session import (
    GuardedShadowSessionController,
    ParityEvidenceEventType,
    ShadowSessionStatus,
)
from src.multi_strategy.shadow import ShadowParityResult

RUNTIME_SHADOW_HOOK_SCHEMA_VERSION = "1.0.0"
_ALLOWED_RUNTIME_STATUSES = {
    "NOT_FOUND",
    "STOPPED",
    "STARTING",
    "RUNNING",
    "STOPPING",
    "FAILED",
    "UNKNOWN",
}


def _freeze(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload))


@dataclass(frozen=True)
class StableRuntimeObservation:
    """One immutable stable double-read of product/runtime status evidence."""

    observed_at: str
    runtime_status: str
    runtime_pid: int | None
    first_read: Mapping[str, Any]
    second_read: Mapping[str, Any]
    source_label: str = "HQE_PRODUCT_RUNTIME_READ_ONLY"
    schema_version: str = RUNTIME_SHADOW_HOOK_SCHEMA_VERSION
    runtime_connected: bool = False
    runtime_control_authorized: bool = False
    lifecycle_write_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    broker_execution_authorized: bool = False

    def __post_init__(self) -> None:
        issues: list[str] = []
        if self.schema_version != RUNTIME_SHADOW_HOOK_SCHEMA_VERSION:
            issues.append("unsupported runtime shadow hook schema version")
        if not str(self.observed_at).strip():
            issues.append("observed_at is required")
        if not str(self.source_label).strip():
            issues.append("source_label is required")
        status = str(self.runtime_status).upper()
        if status not in _ALLOWED_RUNTIME_STATUSES:
            issues.append("unsupported runtime_status")
        if self.runtime_pid is not None:
            if not isinstance(self.runtime_pid, int) or self.runtime_pid < 1:
                issues.append("runtime_pid must be a positive integer or null")
        if not isinstance(self.first_read, Mapping):
            issues.append("first_read must be a mapping")
        if not isinstance(self.second_read, Mapping):
            issues.append("second_read must be a mapping")
        if (
            self.runtime_connected
            or self.runtime_control_authorized
            or self.lifecycle_write_authorized
            or self.state_write_authorized
            or self.ledger_write_authorized
            or self.broker_execution_authorized
        ):
            issues.append(
                "runtime observation cannot connect/control runtime or authorize "
                "lifecycle/state/ledger/broker writes"
            )
        if issues:
            raise RuntimeShadowHookError("; ".join(issues))

        first = dict(self.first_read)
        second = dict(self.second_read)
        if canonical_mapping_hash(first) != canonical_mapping_hash(second):
            raise RuntimeShadowHookError(
                "runtime observation is unstable across double-read"
            )
        object.__setattr__(self, "runtime_status", status)
        object.__setattr__(self, "first_read", _freeze(first))
        object.__setattr__(self, "second_read", _freeze(second))

    @property
    def payload_hash(self) -> str:
        return canonical_mapping_hash(self.first_read)

    @property
    def observation_hash(self) -> str:
        return canonical_mapping_hash(
            {
                "schema_version": self.schema_version,
                "observed_at": self.observed_at,
                "runtime_status": self.runtime_status,
                "runtime_pid": self.runtime_pid,
                "source_label": self.source_label,
                "payload_hash": self.payload_hash,
                "runtime_connected": False,
                "runtime_control_authorized": False,
                "lifecycle_write_authorized": False,
                "state_write_authorized": False,
                "ledger_write_authorized": False,
                "broker_execution_authorized": False,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observed_at": self.observed_at,
            "runtime_status": self.runtime_status,
            "runtime_pid": self.runtime_pid,
            "source_label": self.source_label,
            "payload_hash": self.payload_hash,
            "observation_hash": self.observation_hash,
            "runtime_connected": False,
            "runtime_control_authorized": False,
            "lifecycle_write_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "broker_execution_authorized": False,
        }


@dataclass(frozen=True)
class RuntimeShadowHookResult:
    """One parity cycle bound to immutable runtime observation evidence."""

    observation: StableRuntimeObservation
    parity_result: ShadowParityResult
    journal_record_hash: str
    schema_version: str = RUNTIME_SHADOW_HOOK_SCHEMA_VERSION
    runtime_connected: bool = False
    runtime_cutover_performed: bool = False
    state_written: bool = False
    ledger_written: bool = False
    broker_execution_performed: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_SHADOW_HOOK_SCHEMA_VERSION:
            raise RuntimeShadowHookError(
                "unsupported runtime shadow result schema version"
            )
        if not self.journal_record_hash:
            raise RuntimeShadowHookError("journal_record_hash is required")
        if (
            self.runtime_connected
            or self.runtime_cutover_performed
            or self.state_written
            or self.ledger_written
            or self.broker_execution_performed
        ):
            raise RuntimeShadowHookError(
                "runtime shadow result contains forbidden lifecycle flags"
            )

    @property
    def result_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "observation": self.observation.to_dict(),
            "parity_result_hash": self.parity_result.result_hash,
            "parity_status": self.parity_result.status.value,
            "signal": self.parity_result.registered_result.decision.signal,
            "option_side": (
                self.parity_result.registered_result.decision.option_side
            ),
            "journal_record_hash": self.journal_record_hash,
            "runtime_connected": False,
            "runtime_cutover_performed": False,
            "state_written": False,
            "ledger_written": False,
            "broker_execution_performed": False,
        }
        if include_hash:
            payload["result_hash"] = self.result_hash
        return payload


class ReadOnlyProductRuntimeShadowHook:
    """Bind stable runtime observations to a guarded offline shadow session."""

    def __init__(
        self,
        *,
        controller: GuardedShadowSessionController,
        runtime_connected: bool = False,
    ) -> None:
        if runtime_connected:
            raise RuntimeShadowHookError(
                "runtime shadow hook cannot connect to canonical runtime"
            )
        self._controller = controller
        self.runtime_connected = False

    def observe_cycle(
        self,
        *,
        cycle_id: str,
        event_time: str,
        observation: StableRuntimeObservation,
        request: Any,
    ) -> RuntimeShadowHookResult:
        if self._controller.status is not ShadowSessionStatus.RUNNING:
            raise RuntimeShadowHookError(
                "runtime shadow hook requires a RUNNING guarded session"
            )
        if observation.observed_at != event_time:
            raise RuntimeShadowHookError(
                "runtime observation time must match parity event_time"
            )

        result = self._controller.run_cycle(
            cycle_id=cycle_id,
            event_time=event_time,
            request=request,
            evidence_details={
                "runtime_observation_hash": observation.observation_hash,
                "runtime_payload_hash": observation.payload_hash,
                "runtime_status_observed": observation.runtime_status,
                "runtime_pid_observed": observation.runtime_pid,
                "runtime_source_label": observation.source_label,
                "runtime_observation_stable": True,
                "runtime_observer_read_only": True,
            },
        )
        records = self._controller.journal_records()
        if not records:
            raise RuntimeShadowHookError(
                "parity journal is empty after runtime shadow cycle"
            )
        record = records[-1]
        if record.event_type not in {
            ParityEvidenceEventType.PARITY_MATCH,
            ParityEvidenceEventType.PARITY_MISMATCH,
        }:
            raise RuntimeShadowHookError(
                "last parity journal record is not a parity cycle"
            )
        if record.cycle_id != cycle_id:
            raise RuntimeShadowHookError(
                "last parity journal record cycle identity mismatch"
            )
        if (
            record.details.get("runtime_observation_hash")
            != observation.observation_hash
        ):
            raise RuntimeShadowHookError(
                "journal runtime observation identity mismatch"
            )
        return RuntimeShadowHookResult(
            observation=observation,
            parity_result=result,
            journal_record_hash=record.record_hash,
        )
