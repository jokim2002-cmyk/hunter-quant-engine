"""Read-only operator cutover checklist for HQE multi-strategy evidence.

The checklist converts a disabled cutover-readiness certificate and its
operator view into a deterministic review artifact.  It never grants
activation, selection, lifecycle, runtime, broker, or real-money authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.multi_strategy.cutover_certificate import (
    CutoverCertificateError,
    DisabledCutoverCertificateStatus,
    DisabledCutoverReadinessCertificate,
)
from src.multi_strategy.cutover_certificate_view import (
    DisabledCutoverCertificateView,
)
from src.multi_strategy.execution import canonical_mapping_hash

OPERATOR_CHECKLIST_SCHEMA_VERSION = "1.0.0"
OPERATOR_CHECKLIST_MODE = "READ_ONLY_OPERATOR_CUTOVER_CHECKLIST"


class OperatorChecklistStatus(str, Enum):
    READY_REVIEW_EXPORT_DISABLED = "READY_REVIEW_EXPORT_DISABLED"
    BLOCKED_CERTIFICATE = "BLOCKED_CERTIFICATE"
    BLOCKED_VIEW = "BLOCKED_VIEW"
    BLOCKED_IDENTITY = "BLOCKED_IDENTITY"
    BLOCKED_EVIDENCE = "BLOCKED_EVIDENCE"


@dataclass(frozen=True)
class OperatorChecklistItem:
    code: str
    label: str
    passed: bool
    evidence_hash: str
    detail: str

    def __post_init__(self) -> None:
        if not self.code or not self.label or not self.evidence_hash or not self.detail:
            raise CutoverCertificateError("checklist item fields are required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "passed": self.passed,
            "evidence_hash": self.evidence_hash,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ReadOnlyOperatorCutoverChecklist:
    status: OperatorChecklistStatus
    strategy_id: str
    strategy_version: str
    certificate_hash: str
    certificate_view_hash: str
    items: tuple[OperatorChecklistItem, ...]
    blockers: tuple[str, ...]
    schema_version: str = OPERATOR_CHECKLIST_SCHEMA_VERSION
    mode: str = OPERATOR_CHECKLIST_MODE
    read_only: bool = True
    human_review_ready: bool = False
    export_authorized: bool = False
    activation_authorized: bool = False
    strategy_switch_authorized: bool = False
    selection_write_authorized: bool = False
    lifecycle_write_authorized: bool = False
    state_write_authorized: bool = False
    ledger_write_authorized: bool = False
    runtime_control_authorized: bool = False
    runtime_cutover_authorized: bool = False
    broker_execution_authorized: bool = False
    real_money_authorized: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != OPERATOR_CHECKLIST_SCHEMA_VERSION:
            raise CutoverCertificateError("unsupported operator checklist schema")
        if self.mode != OPERATOR_CHECKLIST_MODE:
            raise CutoverCertificateError("invalid operator checklist mode")
        if not self.read_only:
            raise CutoverCertificateError("operator checklist must remain read-only")
        if any(
            (
                self.export_authorized,
                self.activation_authorized,
                self.strategy_switch_authorized,
                self.selection_write_authorized,
                self.lifecycle_write_authorized,
                self.state_write_authorized,
                self.ledger_write_authorized,
                self.runtime_control_authorized,
                self.runtime_cutover_authorized,
                self.broker_execution_authorized,
                self.real_money_authorized,
            )
        ):
            raise CutoverCertificateError("operator checklist cannot grant authority")
        if not self.strategy_id or not self.strategy_version:
            raise CutoverCertificateError("operator checklist strategy identity is required")
        if not self.certificate_hash or not self.certificate_view_hash:
            raise CutoverCertificateError("operator checklist evidence hashes are required")
        if not self.items:
            raise CutoverCertificateError("operator checklist requires review items")
        if self.status is OperatorChecklistStatus.READY_REVIEW_EXPORT_DISABLED:
            if self.blockers:
                raise CutoverCertificateError("ready checklist cannot contain blockers")
            if not all(item.passed for item in self.items):
                raise CutoverCertificateError("ready checklist requires all items to pass")
            if not self.human_review_ready:
                raise CutoverCertificateError("ready checklist must be human-review ready")
        else:
            if not self.blockers:
                raise CutoverCertificateError("blocked checklist requires blockers")
            if self.human_review_ready:
                raise CutoverCertificateError("blocked checklist cannot be review ready")

    @property
    def checklist_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "status": self.status.value,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "certificate_hash": self.certificate_hash,
            "certificate_view_hash": self.certificate_view_hash,
            "items": [item.to_dict() for item in self.items],
            "blockers": list(self.blockers),
            "read_only": True,
            "human_review_ready": self.human_review_ready,
            "export_authorized": False,
            "activation_authorized": False,
            "strategy_switch_authorized": False,
            "selection_write_authorized": False,
            "lifecycle_write_authorized": False,
            "state_write_authorized": False,
            "ledger_write_authorized": False,
            "runtime_control_authorized": False,
            "runtime_cutover_authorized": False,
            "broker_execution_authorized": False,
            "real_money_authorized": False,
        }
        if include_hash:
            payload["checklist_hash"] = self.checklist_hash
        return payload


def _item(
    code: str,
    label: str,
    passed: bool,
    evidence_hash: str,
    detail: str,
) -> OperatorChecklistItem:
    return OperatorChecklistItem(
        code=code,
        label=label,
        passed=passed,
        evidence_hash=evidence_hash,
        detail=detail,
    )


def build_operator_cutover_checklist(
    certificate: DisabledCutoverReadinessCertificate,
    view: DisabledCutoverCertificateView,
) -> ReadOnlyOperatorCutoverChecklist:
    """Build a deterministic fail-closed operator review checklist."""

    identity_ok = (
        view.strategy_id == certificate.strategy_id
        and view.strategy_version == certificate.strategy_version
        and view.selection_hash == certificate.selection_hash
        and view.certificate_hash == certificate.certificate_hash
    )
    certificate_ready = (
        certificate.status
        is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED
        and certificate.human_review_ready
        and not certificate.blockers
    )
    view_ready = (
        view.status is certificate.status
        and view.human_review_ready
        and view.read_only
        and not view.blockers
        and view.recommendation
        == "READY_FOR_HUMAN_CUTOVER_REVIEW_ACTIVATION_DISABLED"
    )
    evidence_ok = bool(certificate.canonical_evidence_hashes) and all(
        (
            certificate.selection_hash,
            certificate.one_active_set_hash,
            certificate.lifecycle_plan_hash,
            certificate.activation_preflight_hash,
            certificate.reconciliation_hash,
            certificate.reconciliation_view_hash,
            certificate.sandbox_bundle_hash,
            certificate.canonical_plan_hash,
        )
    )
    zero_authority = not any(
        (
            certificate.activation_authorized,
            certificate.strategy_switch_authorized,
            certificate.selection_write_authorized,
            certificate.lifecycle_write_authorized,
            certificate.state_write_authorized,
            certificate.ledger_write_authorized,
            certificate.runtime_connection_authorized,
            certificate.runtime_control_authorized,
            certificate.runtime_cutover_authorized,
            certificate.broker_execution_authorized,
            certificate.real_money_authorized,
            view.activation_button_enabled,
            view.strategy_switch_enabled,
            view.selection_write_enabled,
            view.lifecycle_write_enabled,
            view.state_write_enabled,
            view.ledger_write_enabled,
            view.runtime_control_enabled,
            view.runtime_cutover_enabled,
            view.broker_execution_enabled,
            view.real_money_enabled,
        )
    )

    items = (
        _item(
            "CERTIFICATE_READY",
            "Disabled certificate is ready for human review",
            certificate_ready,
            certificate.certificate_hash,
            certificate.status.value,
        ),
        _item(
            "VIEW_READY",
            "Read-only operator view matches certificate",
            view_ready,
            view.view_hash,
            view.recommendation,
        ),
        _item(
            "IDENTITY_CHAIN",
            "Strategy and evidence identity chain matches",
            identity_ok,
            certificate.selection_hash,
            certificate.implementation_key,
        ),
        _item(
            "ONE_ACTIVE_BINDING",
            "Exactly one reviewed strategy is bound",
            certificate.active_strategy_count == 1
            and certificate.one_active_strategy_enforced,
            certificate.one_active_set_hash,
            "one-active invariant",
        ),
        _item(
            "LIFECYCLE_PLAN_BINDING",
            "Disabled lifecycle plan is bound",
            bool(certificate.lifecycle_plan_hash),
            certificate.lifecycle_plan_hash,
            "lifecycle writes disabled",
        ),
        _item(
            "RECONCILIATION_BINDING",
            "Flat reconciliation evidence is bound",
            bool(certificate.reconciliation_hash)
            and bool(certificate.reconciliation_view_hash),
            certificate.reconciliation_hash,
            certificate.reconciliation_view_hash,
        ),
        _item(
            "CANONICAL_EVIDENCE_HASHES",
            "Canonical evidence hashes are present",
            evidence_ok,
            certificate.canonical_plan_hash,
            ",".join(sorted(certificate.canonical_evidence_hashes)),
        ),
        _item(
            "ZERO_AUTHORITY",
            "All activation and execution authorities remain disabled",
            zero_authority,
            certificate.certificate_hash,
            "zero activation/cutover/broker authority",
        ),
    )

    blockers: list[str] = []
    if not identity_ok:
        blockers.append("certificate/view identity mismatch")
    if not certificate_ready:
        blockers.append("certificate is not READY_FLAT_DISABLED")
    if not view_ready:
        blockers.append("certificate view is not ready and read-only")
    if not evidence_ok:
        blockers.append("required evidence hashes are incomplete")
    if not zero_authority:
        blockers.append("unsafe authority flag detected")
    for item in items:
        if not item.passed and item.detail not in blockers:
            blockers.append(f"checklist item failed: {item.code}")

    if not identity_ok:
        status = OperatorChecklistStatus.BLOCKED_IDENTITY
    elif not certificate_ready:
        status = OperatorChecklistStatus.BLOCKED_CERTIFICATE
    elif not view_ready:
        status = OperatorChecklistStatus.BLOCKED_VIEW
    elif not evidence_ok or not zero_authority:
        status = OperatorChecklistStatus.BLOCKED_EVIDENCE
    else:
        status = OperatorChecklistStatus.READY_REVIEW_EXPORT_DISABLED

    return ReadOnlyOperatorCutoverChecklist(
        status=status,
        strategy_id=certificate.strategy_id,
        strategy_version=certificate.strategy_version,
        certificate_hash=certificate.certificate_hash,
        certificate_view_hash=view.view_hash,
        items=items,
        blockers=tuple(blockers),
        human_review_ready=(
            status is OperatorChecklistStatus.READY_REVIEW_EXPORT_DISABLED
        ),
    )
