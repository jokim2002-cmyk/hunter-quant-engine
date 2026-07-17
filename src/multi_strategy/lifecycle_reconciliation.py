"""Read-only reconciliation of Phase 4K sandbox lifecycle evidence.

This module compares one tamper-evident sandbox lifecycle bundle with the
existing canonical Module 131 paper-lifecycle evidence represented by the
read-only Phase 4B migration planner. It never writes either evidence source,
never activates a strategy, and never connects to the canonical runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.lifecycle_journal import SandboxLifecycleBundle
from src.multi_strategy.migration import LegacyMigrationPlan, MigrationReadiness
from src.multi_strategy.selection import StrategySelectionSnapshot
from src.multi_strategy.storage import PositionLifecycle

RECONCILIATION_SCHEMA_VERSION = "1.0.0"


class LifecycleReconciliationError(ValueError):
    """Raised when evidence cannot be reconciled safely."""


class LifecycleReconciliationStatus(str, Enum):
    MATCH_FLAT = "MATCH_FLAT"
    MATCH_OPEN = "MATCH_OPEN"
    DIVERGED_LIFECYCLE = "DIVERGED_LIFECYCLE"
    DIVERGED_POSITION = "DIVERGED_POSITION"
    DIVERGED_LEDGER = "DIVERGED_LEDGER"
    BLOCKED_RUNTIME_RUNNING = "BLOCKED_RUNTIME_RUNNING"
    BLOCKED_CANONICAL_EVIDENCE = "BLOCKED_CANONICAL_EVIDENCE"
    NO_CANONICAL_EVIDENCE = "NO_CANONICAL_EVIDENCE"


@dataclass(frozen=True)
class LifecycleSemanticObservation:
    """Format-independent lifecycle facts used for reconciliation."""

    lifecycle: str
    opened_count: int
    closed_count: int
    unmatched_open_count: int
    option_side: str = ""
    option_symbol: str = ""
    quantity: int = 0
    entry: float | None = None

    def __post_init__(self) -> None:
        if self.lifecycle not in {"FLAT", "OPEN", "CLOSED"}:
            raise LifecycleReconciliationError("invalid semantic lifecycle")
        for label, value in (
            ("opened_count", self.opened_count),
            ("closed_count", self.closed_count),
            ("unmatched_open_count", self.unmatched_open_count),
            ("quantity", self.quantity),
        ):
            if not isinstance(value, int) or value < 0:
                raise LifecycleReconciliationError(
                    f"{label} must be a non-negative integer"
                )
        if self.unmatched_open_count != self.opened_count - self.closed_count:
            raise LifecycleReconciliationError("lifecycle balance is inconsistent")
        if self.lifecycle == "OPEN":
            if self.unmatched_open_count != 1:
                raise LifecycleReconciliationError(
                    "OPEN observation requires one unmatched position"
                )
            if self.option_side not in {"CE_BUY", "PE_BUY"}:
                raise LifecycleReconciliationError("OPEN observation side is invalid")
            if not self.option_symbol:
                raise LifecycleReconciliationError(
                    "OPEN observation option_symbol is required"
                )
            if self.quantity <= 0:
                raise LifecycleReconciliationError(
                    "OPEN observation quantity must be positive"
                )
            if self.entry is None or self.entry <= 0:
                raise LifecycleReconciliationError(
                    "OPEN observation entry must be positive"
                )
        elif self.unmatched_open_count != 0:
            raise LifecycleReconciliationError(
                "non-OPEN observation cannot contain an unmatched position"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lifecycle": self.lifecycle,
            "opened_count": self.opened_count,
            "closed_count": self.closed_count,
            "unmatched_open_count": self.unmatched_open_count,
            "option_side": self.option_side,
            "option_symbol": self.option_symbol,
            "quantity": self.quantity,
            "entry": self.entry,
        }


def _sandbox_semantics(
    bundle: SandboxLifecycleBundle,
) -> LifecycleSemanticObservation:
    opened = sum(event.transition == "FLAT->OPEN" for event in bundle.events)
    closed = sum(event.transition in {"OPEN->CLOSED", "HELD->CLOSED"} for event in bundle.events)
    unmatched = opened - closed
    state = bundle.current_state
    if state.lifecycle in {PositionLifecycle.OPEN, PositionLifecycle.HELD}:
        lifecycle = "OPEN"
        position = dict(state.position)
        side = str(position.get("option_side") or position.get("side") or "").upper()
        symbol = str(position.get("option_symbol") or "")
        quantity = int(position.get("quantity") or 0)
        entry_value = position.get("entry")
        entry = None if entry_value in (None, "") else float(entry_value)
    elif state.lifecycle is PositionLifecycle.FLAT:
        lifecycle = "FLAT"
        side = ""
        symbol = ""
        quantity = 0
        entry = None
    else:
        lifecycle = "CLOSED"
        side = ""
        symbol = ""
        quantity = 0
        entry = None
    return LifecycleSemanticObservation(
        lifecycle=lifecycle,
        opened_count=opened,
        closed_count=closed,
        unmatched_open_count=unmatched,
        option_side=side,
        option_symbol=symbol,
        quantity=quantity,
        entry=entry,
    )


def _canonical_semantics(
    plan: LegacyMigrationPlan,
) -> LifecycleSemanticObservation:
    lifecycle = plan.proposed_state.lifecycle.value
    if lifecycle == PositionLifecycle.HELD.value:
        lifecycle = "OPEN"
    position = dict(plan.legacy_open_position)
    if lifecycle == "OPEN":
        side = str(position.get("side") or position.get("option_side") or "").upper()
        symbol = str(position.get("option_symbol") or "")
        quantity = int(position.get("quantity") or 0)
        entry_value = position.get("entry")
        entry = None if entry_value in (None, "") else float(entry_value)
    else:
        side = ""
        symbol = ""
        quantity = 0
        entry = None
    return LifecycleSemanticObservation(
        lifecycle=lifecycle,
        opened_count=plan.ledger.opened_count,
        closed_count=plan.ledger.closed_count,
        unmatched_open_count=plan.ledger.unmatched_open_count,
        option_side=side,
        option_symbol=symbol,
        quantity=quantity,
        entry=entry,
    )


@dataclass(frozen=True)
class ReadOnlyLifecycleReconciliation:
    """Immutable read-only reconciliation result."""

    status: LifecycleReconciliationStatus
    strategy_id: str
    strategy_version: str
    selection_hash: str
    sandbox_bundle_hash: str
    canonical_plan_hash: str
    sandbox: LifecycleSemanticObservation
    canonical: LifecycleSemanticObservation | None
    canonical_evidence_hashes: Mapping[str, str]
    differences: tuple[str, ...] = ()
    schema_version: str = RECONCILIATION_SCHEMA_VERSION
    read_only: bool = True
    canonical_files_written: bool = False
    sandbox_files_written: bool = False
    strategy_activation_authorized: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != RECONCILIATION_SCHEMA_VERSION:
            raise LifecycleReconciliationError(
                "unsupported reconciliation schema version"
            )
        if not self.read_only:
            raise LifecycleReconciliationError("reconciliation must remain read-only")
        if any(
            (
                self.canonical_files_written,
                self.sandbox_files_written,
                self.strategy_activation_authorized,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise LifecycleReconciliationError(
                "reconciliation cannot authorize writes or execution"
            )
        if not self.strategy_id or not self.strategy_version:
            raise LifecycleReconciliationError("strategy identity is required")
        if not self.selection_hash or not self.sandbox_bundle_hash:
            raise LifecycleReconciliationError("selection and bundle hashes are required")
        if self.status in {
            LifecycleReconciliationStatus.MATCH_FLAT,
            LifecycleReconciliationStatus.MATCH_OPEN,
        } and self.differences:
            raise LifecycleReconciliationError("matching result cannot contain differences")
        object.__setattr__(
            self,
            "canonical_evidence_hashes",
            MappingProxyType(dict(sorted(self.canonical_evidence_hashes.items()))),
        )

    @property
    def matched(self) -> bool:
        return self.status in {
            LifecycleReconciliationStatus.MATCH_FLAT,
            LifecycleReconciliationStatus.MATCH_OPEN,
        }

    @property
    def reconciliation_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "matched": self.matched,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "sandbox_bundle_hash": self.sandbox_bundle_hash,
            "canonical_plan_hash": self.canonical_plan_hash,
            "sandbox": self.sandbox.to_dict(),
            "canonical": None if self.canonical is None else self.canonical.to_dict(),
            "canonical_evidence_hashes": dict(self.canonical_evidence_hashes),
            "differences": list(self.differences),
            "read_only": self.read_only,
            "canonical_files_written": self.canonical_files_written,
            "sandbox_files_written": self.sandbox_files_written,
            "strategy_activation_authorized": self.strategy_activation_authorized,
            "runtime_cutover_authorized": self.runtime_cutover_authorized,
            "broker_execution_authorized": self.broker_execution_authorized,
            "real_money_authorized": self.real_money_authorized,
        }
        if include_hash:
            payload["reconciliation_hash"] = self.reconciliation_hash
        return payload


def _evidence_hashes(plan: LegacyMigrationPlan) -> dict[str, str]:
    return {
        name: evidence.sha256
        for name, evidence in sorted(plan.evidence.items())
        if evidence.exists
    }


def reconcile_lifecycle_evidence(
    *,
    selection: StrategySelectionSnapshot,
    sandbox_bundle: SandboxLifecycleBundle,
    canonical_plan: LegacyMigrationPlan,
) -> ReadOnlyLifecycleReconciliation:
    """Compare stable canonical evidence with a sandbox bundle without writes."""

    if (
        selection.strategy_id != CURRENT_SMC_STRATEGY_ID
        or selection.strategy_version != CURRENT_SMC_STRATEGY_VERSION
        or selection.implementation_key != CURRENT_SMC_IMPLEMENTATION_KEY
    ):
        raise LifecycleReconciliationError(
            "reconciliation supports reviewed current SMC only"
        )
    if sandbox_bundle.selection.selection_hash != selection.selection_hash:
        raise LifecycleReconciliationError("sandbox bundle selection mismatch")
    if canonical_plan.selection_hash != selection.selection_hash:
        raise LifecycleReconciliationError("canonical plan selection mismatch")

    sandbox = _sandbox_semantics(sandbox_bundle)
    evidence_hashes = _evidence_hashes(canonical_plan)

    def result(
        status: LifecycleReconciliationStatus,
        canonical: LifecycleSemanticObservation | None,
        differences: tuple[str, ...] = (),
    ) -> ReadOnlyLifecycleReconciliation:
        return ReadOnlyLifecycleReconciliation(
            status=status,
            strategy_id=selection.strategy_id,
            strategy_version=selection.strategy_version,
            selection_hash=selection.selection_hash,
            sandbox_bundle_hash=sandbox_bundle.bundle_hash,
            canonical_plan_hash=canonical_plan.plan_hash,
            sandbox=sandbox,
            canonical=canonical,
            canonical_evidence_hashes=evidence_hashes,
            differences=differences,
        )

    if canonical_plan.readiness is MigrationReadiness.NO_LEGACY_DATA:
        return result(
            LifecycleReconciliationStatus.NO_CANONICAL_EVIDENCE,
            None,
            ("no canonical Module 131 evidence found",),
        )
    if canonical_plan.readiness is MigrationReadiness.BLOCKED_RUNTIME_RUNNING:
        return result(
            LifecycleReconciliationStatus.BLOCKED_RUNTIME_RUNNING,
            None,
            ("canonical paper runtime appears to be running",),
        )
    if canonical_plan.readiness in {
        MigrationReadiness.BLOCKED_CORRUPT_STATE,
        MigrationReadiness.BLOCKED_LEDGER_INCONSISTENT,
        MigrationReadiness.BLOCKED_SAFETY_VIOLATION,
    }:
        return result(
            LifecycleReconciliationStatus.BLOCKED_CANONICAL_EVIDENCE,
            None,
            tuple(canonical_plan.issues) or ("canonical evidence is blocked",),
        )

    canonical = _canonical_semantics(canonical_plan)
    if sandbox.lifecycle != canonical.lifecycle:
        return result(
            LifecycleReconciliationStatus.DIVERGED_LIFECYCLE,
            canonical,
            (
                "lifecycle differs: "
                f"sandbox={sandbox.lifecycle}, canonical={canonical.lifecycle}",
            ),
        )

    ledger_differences: list[str] = []
    for label in ("opened_count", "closed_count", "unmatched_open_count"):
        sandbox_value = getattr(sandbox, label)
        canonical_value = getattr(canonical, label)
        if sandbox_value != canonical_value:
            ledger_differences.append(
                f"{label} differs: sandbox={sandbox_value}, canonical={canonical_value}"
            )
    if ledger_differences:
        return result(
            LifecycleReconciliationStatus.DIVERGED_LEDGER,
            canonical,
            tuple(ledger_differences),
        )

    if canonical.lifecycle == "OPEN":
        position_differences: list[str] = []
        for label in ("option_side", "option_symbol", "quantity", "entry"):
            sandbox_value = getattr(sandbox, label)
            canonical_value = getattr(canonical, label)
            if sandbox_value != canonical_value:
                position_differences.append(
                    f"{label} differs: sandbox={sandbox_value}, canonical={canonical_value}"
                )
        if position_differences:
            return result(
                LifecycleReconciliationStatus.DIVERGED_POSITION,
                canonical,
                tuple(position_differences),
            )
        return result(LifecycleReconciliationStatus.MATCH_OPEN, canonical)

    return result(LifecycleReconciliationStatus.MATCH_FLAT, canonical)
