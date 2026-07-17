"""Disabled cutover-readiness certificate for HQE multi-strategy evidence.

The certificate binds the selected reviewed strategy, one-active invariant,
disabled lifecycle plan, and Phase 4L reconciliation chain into one immutable
review artifact. It may classify evidence as ready for later human review, but
it never grants activation, strategy switching, canonical writes, runtime
cutover, broker execution, or real-money authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.lifecycle_adapter import (
    DisabledCanonicalLifecyclePlan,
    DisabledLifecyclePlanStatus,
)
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationStatus,
    ReadOnlyLifecycleReconciliation,
)
from src.multi_strategy.lifecycle_reconciliation_view import (
    ReadOnlyLifecycleReconciliationView,
)
from src.multi_strategy.one_active import DisabledOneActiveStrategySet
from src.multi_strategy.selection import StrategySelectionSnapshot

CUTOVER_CERTIFICATE_SCHEMA_VERSION = "1.0.0"
CUTOVER_CERTIFICATE_MODE = "DISABLED_CUTOVER_READINESS_CERTIFICATE"


class CutoverCertificateError(ValueError):
    """Raised when a disabled certificate is structurally unsafe."""


class DisabledCutoverCertificateStatus(str, Enum):
    """Readiness classification; no status authorizes cutover."""

    READY_FLAT_DISABLED = "READY_FLAT_DISABLED"
    BLOCKED_OPEN_POSITION = "BLOCKED_OPEN_POSITION"
    BLOCKED_RUNTIME_ACTIVE = "BLOCKED_RUNTIME_ACTIVE"
    BLOCKED_RECONCILIATION = "BLOCKED_RECONCILIATION"
    BLOCKED_EVIDENCE = "BLOCKED_EVIDENCE"
    BLOCKED_IDENTITY = "BLOCKED_IDENTITY"


@dataclass(frozen=True)
class DisabledCutoverReadinessCertificate:
    """Immutable zero-authority evidence certificate."""

    status: DisabledCutoverCertificateStatus
    strategy_id: str
    strategy_version: str
    implementation_key: str
    selection_hash: str
    one_active_set_hash: str
    lifecycle_plan_hash: str
    activation_preflight_hash: str
    reconciliation_hash: str
    reconciliation_view_hash: str
    sandbox_bundle_hash: str
    canonical_plan_hash: str
    canonical_evidence_hashes: Mapping[str, str]
    blockers: tuple[str, ...]
    schema_version: str = CUTOVER_CERTIFICATE_SCHEMA_VERSION
    mode: str = CUTOVER_CERTIFICATE_MODE
    active_strategy_count: int = 1
    one_active_strategy_enforced: bool = True
    activation_authorized: bool = False
    strategy_switch_authorized: bool = False
    selection_write_authorized: bool = False
    lifecycle_write_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    runtime_connection_authorized: bool = False
    runtime_control_authorized: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != CUTOVER_CERTIFICATE_SCHEMA_VERSION:
            raise CutoverCertificateError("unsupported cutover certificate schema")
        if self.mode != CUTOVER_CERTIFICATE_MODE:
            raise CutoverCertificateError("invalid cutover certificate mode")
        if self.active_strategy_count != 1:
            raise CutoverCertificateError(
                "cutover certificate requires exactly one active strategy"
            )
        if not self.one_active_strategy_enforced:
            raise CutoverCertificateError(
                "one-active strategy enforcement must remain enabled"
            )
        if any(
            (
                self.activation_authorized,
                self.strategy_switch_authorized,
                self.selection_write_authorized,
                self.lifecycle_write_authorized,
                self.state_write_authorized,
                self.ledger_write_authorized,
                self.runtime_connection_authorized,
                self.runtime_control_authorized,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise CutoverCertificateError(
                "disabled cutover certificate cannot grant authority"
            )
        for label, value in (
            ("strategy_id", self.strategy_id),
            ("strategy_version", self.strategy_version),
            ("implementation_key", self.implementation_key),
            ("selection_hash", self.selection_hash),
            ("one_active_set_hash", self.one_active_set_hash),
            ("lifecycle_plan_hash", self.lifecycle_plan_hash),
            ("activation_preflight_hash", self.activation_preflight_hash),
            ("reconciliation_hash", self.reconciliation_hash),
            ("reconciliation_view_hash", self.reconciliation_view_hash),
            ("sandbox_bundle_hash", self.sandbox_bundle_hash),
            ("canonical_plan_hash", self.canonical_plan_hash),
        ):
            if not value:
                raise CutoverCertificateError(f"{label} is required")
        if self.status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED:
            if self.blockers:
                raise CutoverCertificateError(
                    "READY_FLAT_DISABLED certificate cannot contain blockers"
                )
            if not self.canonical_evidence_hashes:
                raise CutoverCertificateError(
                    "ready certificate requires canonical evidence hashes"
                )
        elif not self.blockers:
            raise CutoverCertificateError(
                "blocked cutover certificate requires blockers"
            )
        object.__setattr__(
            self,
            "canonical_evidence_hashes",
            MappingProxyType(dict(sorted(self.canonical_evidence_hashes.items()))),
        )

    @property
    def human_review_ready(self) -> bool:
        return self.status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED

    @property
    def certificate_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "status": self.status.value,
            "human_review_ready": self.human_review_ready,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "implementation_key": self.implementation_key,
            "selection_hash": self.selection_hash,
            "one_active_set_hash": self.one_active_set_hash,
            "lifecycle_plan_hash": self.lifecycle_plan_hash,
            "activation_preflight_hash": self.activation_preflight_hash,
            "reconciliation_hash": self.reconciliation_hash,
            "reconciliation_view_hash": self.reconciliation_view_hash,
            "sandbox_bundle_hash": self.sandbox_bundle_hash,
            "canonical_plan_hash": self.canonical_plan_hash,
            "canonical_evidence_hashes": dict(self.canonical_evidence_hashes),
            "blockers": list(self.blockers),
            "active_strategy_count": 1,
            "one_active_strategy_enforced": True,
            "activation_authorized": False,
            "strategy_switch_authorized": False,
            "selection_write_authorized": False,
            "lifecycle_write_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "runtime_connection_authorized": False,
            "runtime_control_authorized": False,
            "runtime_cutover_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["certificate_hash"] = self.certificate_hash
        return payload


def build_disabled_cutover_readiness_certificate(
    *,
    selection: StrategySelectionSnapshot,
    one_active: DisabledOneActiveStrategySet,
    lifecycle_plan: DisabledCanonicalLifecyclePlan,
    reconciliation: ReadOnlyLifecycleReconciliation,
    reconciliation_view: ReadOnlyLifecycleReconciliationView,
) -> DisabledCutoverReadinessCertificate:
    """Build a fail-closed review certificate with zero execution authority."""

    identity_issues: list[str] = []
    if one_active.selection.selection_hash != selection.selection_hash:
        identity_issues.append("one-active selection does not match selection")
    if lifecycle_plan.strategy_id != selection.strategy_id:
        identity_issues.append("lifecycle plan strategy_id does not match")
    if lifecycle_plan.strategy_version != selection.strategy_version:
        identity_issues.append("lifecycle plan strategy_version does not match")
    if lifecycle_plan.implementation_key != selection.implementation_key:
        identity_issues.append("lifecycle plan implementation_key does not match")
    if lifecycle_plan.selection_hash != selection.selection_hash:
        identity_issues.append("lifecycle plan selection_hash does not match")
    if lifecycle_plan.one_active_set_hash != one_active.set_hash:
        identity_issues.append("lifecycle plan one-active hash does not match")
    if reconciliation.strategy_id != selection.strategy_id:
        identity_issues.append("reconciliation strategy_id does not match")
    if reconciliation.strategy_version != selection.strategy_version:
        identity_issues.append("reconciliation strategy_version does not match")
    if reconciliation.selection_hash != selection.selection_hash:
        identity_issues.append("reconciliation selection_hash does not match")
    if reconciliation_view.strategy_id != selection.strategy_id:
        identity_issues.append("reconciliation view strategy_id does not match")
    if reconciliation_view.strategy_version != selection.strategy_version:
        identity_issues.append("reconciliation view strategy_version does not match")
    if reconciliation_view.selection_hash != selection.selection_hash:
        identity_issues.append("reconciliation view selection_hash does not match")
    if reconciliation_view.reconciliation_hash != reconciliation.reconciliation_hash:
        identity_issues.append("reconciliation view hash does not match result")
    if reconciliation_view.status is not reconciliation.status:
        identity_issues.append("reconciliation view status does not match result")
    if dict(reconciliation_view.canonical_evidence_hashes) != dict(
        reconciliation.canonical_evidence_hashes
    ):
        identity_issues.append("reconciliation view evidence hashes do not match")

    blockers: list[str] = []
    if identity_issues:
        status = DisabledCutoverCertificateStatus.BLOCKED_IDENTITY
        blockers.extend(identity_issues)
    elif (
        lifecycle_plan.status is DisabledLifecyclePlanStatus.BLOCKED_RUNTIME_ACTIVE
        or reconciliation.status
        is LifecycleReconciliationStatus.BLOCKED_RUNTIME_RUNNING
    ):
        status = DisabledCutoverCertificateStatus.BLOCKED_RUNTIME_ACTIVE
        blockers.append("canonical runtime evidence is active")
        blockers.extend(lifecycle_plan.blockers)
        blockers.extend(reconciliation.differences)
    elif (
        lifecycle_plan.status is DisabledLifecyclePlanStatus.BLOCKED_OPEN_POSITION
        or reconciliation.status is LifecycleReconciliationStatus.MATCH_OPEN
    ):
        status = DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION
        blockers.append("canonical lifecycle is not FLAT")
        blockers.extend(lifecycle_plan.blockers)
    elif reconciliation.status is not LifecycleReconciliationStatus.MATCH_FLAT:
        status = DisabledCutoverCertificateStatus.BLOCKED_RECONCILIATION
        blockers.append(
            f"lifecycle reconciliation is {reconciliation.status.value}"
        )
        blockers.extend(reconciliation.differences)
    elif lifecycle_plan.status is not DisabledLifecyclePlanStatus.READY_DISABLED:
        status = DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE
        blockers.append(
            f"disabled lifecycle plan is {lifecycle_plan.status.value}"
        )
        blockers.extend(lifecycle_plan.blockers)
    elif reconciliation_view.recommendation != "MATCH_FLAT_READ_ONLY":
        status = DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE
        blockers.append("reconciliation operator recommendation is not flat-ready")
    elif not reconciliation.canonical_evidence_hashes:
        status = DisabledCutoverCertificateStatus.BLOCKED_EVIDENCE
        blockers.append("canonical evidence hashes are missing")
    else:
        status = DisabledCutoverCertificateStatus.READY_FLAT_DISABLED

    return DisabledCutoverReadinessCertificate(
        status=status,
        strategy_id=selection.strategy_id,
        strategy_version=selection.strategy_version,
        implementation_key=selection.implementation_key,
        selection_hash=selection.selection_hash,
        one_active_set_hash=one_active.set_hash,
        lifecycle_plan_hash=lifecycle_plan.plan_hash,
        activation_preflight_hash=lifecycle_plan.preflight_hash,
        reconciliation_hash=reconciliation.reconciliation_hash,
        reconciliation_view_hash=reconciliation_view.view_hash,
        sandbox_bundle_hash=reconciliation.sandbox_bundle_hash,
        canonical_plan_hash=reconciliation.canonical_plan_hash,
        canonical_evidence_hashes=reconciliation.canonical_evidence_hashes,
        blockers=tuple(dict.fromkeys(blockers)),
    )
