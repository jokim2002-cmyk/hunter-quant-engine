"""Read-only operator view for disabled cutover-readiness certificates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.multi_strategy.cutover_certificate import (
    CutoverCertificateError,
    DisabledCutoverCertificateStatus,
    DisabledCutoverReadinessCertificate,
)
from src.multi_strategy.execution import canonical_mapping_hash

CUTOVER_CERTIFICATE_VIEW_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class DisabledCutoverCertificateView:
    status: DisabledCutoverCertificateStatus
    recommendation: str
    strategy_id: str
    strategy_version: str
    selection_hash: str
    certificate_hash: str
    blockers: tuple[str, ...]
    human_review_ready: bool
    schema_version: str = CUTOVER_CERTIFICATE_VIEW_SCHEMA_VERSION
    read_only: bool = True
    activation_button_enabled: bool = False
    strategy_switch_enabled: bool = False
    selection_write_enabled: bool = False
    lifecycle_write_enabled: bool = False
    state_write_enabled: bool = False
    ledger_write_enabled: bool = False
    runtime_control_enabled: bool = False
    runtime_cutover_enabled: bool = False
    broker_execution_enabled: bool = False
    real_money_enabled: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != CUTOVER_CERTIFICATE_VIEW_SCHEMA_VERSION:
            raise CutoverCertificateError(
                "unsupported cutover certificate view schema"
            )
        if not self.read_only:
            raise CutoverCertificateError(
                "cutover certificate view must remain read-only"
            )
        if any(
            (
                self.activation_button_enabled,
                self.strategy_switch_enabled,
                self.selection_write_enabled,
                self.lifecycle_write_enabled,
                self.state_write_enabled,
                self.ledger_write_enabled,
                self.runtime_control_enabled,
                self.runtime_cutover_enabled,
                self.broker_execution_enabled,
                self.real_money_enabled,
            )
        ):
            raise CutoverCertificateError(
                "cutover certificate view cannot expose mutating controls"
            )
        if self.human_review_ready != (
            self.status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED
        ):
            raise CutoverCertificateError(
                "view readiness must match certificate status"
            )

    @property
    def view_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "recommendation": self.recommendation,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "certificate_hash": self.certificate_hash,
            "blockers": list(self.blockers),
            "human_review_ready": self.human_review_ready,
            "read_only": self.read_only,
            "activation_button_enabled": False,
            "strategy_switch_enabled": False,
            "selection_write_enabled": False,
            "lifecycle_write_enabled": False,
            "state_write_enabled": False,
            "ledger_write_enabled": False,
            "runtime_control_enabled": False,
            "runtime_cutover_enabled": False,
            "broker_execution_enabled": False,
            "real_money_enabled": False,
        }
        if include_hash:
            payload["view_hash"] = self.view_hash
        return payload


def build_cutover_certificate_view(
    certificate: DisabledCutoverReadinessCertificate,
) -> DisabledCutoverCertificateView:
    if certificate.status is DisabledCutoverCertificateStatus.READY_FLAT_DISABLED:
        recommendation = "READY_FOR_HUMAN_CUTOVER_REVIEW_ACTIVATION_DISABLED"
    elif certificate.status is DisabledCutoverCertificateStatus.BLOCKED_OPEN_POSITION:
        recommendation = "WAIT_FOR_FLAT_RECONCILIATION"
    elif certificate.status is DisabledCutoverCertificateStatus.BLOCKED_RUNTIME_ACTIVE:
        recommendation = "STOP_CANONICAL_RUNTIME_AND_REVIEW"
    elif certificate.status is DisabledCutoverCertificateStatus.BLOCKED_RECONCILIATION:
        recommendation = "RESOLVE_RECONCILIATION_DIVERGENCE"
    elif certificate.status is DisabledCutoverCertificateStatus.BLOCKED_IDENTITY:
        recommendation = "REBUILD_EVIDENCE_IDENTITY_CHAIN"
    else:
        recommendation = "RESOLVE_EVIDENCE_BLOCKERS"
    return DisabledCutoverCertificateView(
        status=certificate.status,
        recommendation=recommendation,
        strategy_id=certificate.strategy_id,
        strategy_version=certificate.strategy_version,
        selection_hash=certificate.selection_hash,
        certificate_hash=certificate.certificate_hash,
        blockers=certificate.blockers,
        human_review_ready=certificate.human_review_ready,
    )
