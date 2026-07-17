"""Read-only operator view for lifecycle reconciliation evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from src.multi_strategy.execution import canonical_mapping_hash
from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationError,
    LifecycleReconciliationStatus,
    ReadOnlyLifecycleReconciliation,
)

RECONCILIATION_VIEW_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ReadOnlyLifecycleReconciliationView:
    status: LifecycleReconciliationStatus
    recommendation: str
    strategy_id: str
    strategy_version: str
    selection_hash: str
    reconciliation_hash: str
    sandbox_lifecycle: str
    canonical_lifecycle: str
    sandbox_opened_count: int
    sandbox_closed_count: int
    canonical_opened_count: int | None
    canonical_closed_count: int | None
    differences: tuple[str, ...]
    canonical_evidence_hashes: Mapping[str, str]
    schema_version: str = RECONCILIATION_VIEW_SCHEMA_VERSION
    read_only: bool = True
    strategy_switch_enabled: bool = False
    lifecycle_write_enabled: bool = False
    runtime_cutover_enabled: bool = False
    broker_execution_enabled: bool = False
    real_money_enabled: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != RECONCILIATION_VIEW_SCHEMA_VERSION:
            raise LifecycleReconciliationError(
                "unsupported reconciliation view schema"
            )
        if not self.read_only:
            raise LifecycleReconciliationError("reconciliation view must be read-only")
        if any(
            (
                self.strategy_switch_enabled,
                self.lifecycle_write_enabled,
                self.runtime_cutover_enabled,
                self.broker_execution_enabled,
                self.real_money_enabled,
            )
        ):
            raise LifecycleReconciliationError(
                "reconciliation view cannot expose mutating controls"
            )
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
    def view_hash(self) -> str:
        return canonical_mapping_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "matched": self.matched,
            "recommendation": self.recommendation,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "selection_hash": self.selection_hash,
            "reconciliation_hash": self.reconciliation_hash,
            "sandbox_lifecycle": self.sandbox_lifecycle,
            "canonical_lifecycle": self.canonical_lifecycle,
            "sandbox_opened_count": self.sandbox_opened_count,
            "sandbox_closed_count": self.sandbox_closed_count,
            "canonical_opened_count": self.canonical_opened_count,
            "canonical_closed_count": self.canonical_closed_count,
            "differences": list(self.differences),
            "canonical_evidence_hashes": dict(self.canonical_evidence_hashes),
            "read_only": self.read_only,
            "strategy_switch_enabled": self.strategy_switch_enabled,
            "lifecycle_write_enabled": self.lifecycle_write_enabled,
            "runtime_cutover_enabled": self.runtime_cutover_enabled,
            "broker_execution_enabled": self.broker_execution_enabled,
            "real_money_enabled": self.real_money_enabled,
        }
        if include_hash:
            payload["view_hash"] = self.view_hash
        return payload


def build_reconciliation_view(
    reconciliation: ReadOnlyLifecycleReconciliation,
) -> ReadOnlyLifecycleReconciliationView:
    if reconciliation.status is LifecycleReconciliationStatus.MATCH_FLAT:
        recommendation = "MATCH_FLAT_READ_ONLY"
    elif reconciliation.status is LifecycleReconciliationStatus.MATCH_OPEN:
        recommendation = "MATCH_OPEN_READ_ONLY_SWITCH_BLOCKED"
    else:
        recommendation = "REVIEW_REQUIRED_READ_ONLY"
    canonical = reconciliation.canonical
    return ReadOnlyLifecycleReconciliationView(
        status=reconciliation.status,
        recommendation=recommendation,
        strategy_id=reconciliation.strategy_id,
        strategy_version=reconciliation.strategy_version,
        selection_hash=reconciliation.selection_hash,
        reconciliation_hash=reconciliation.reconciliation_hash,
        sandbox_lifecycle=reconciliation.sandbox.lifecycle,
        canonical_lifecycle="" if canonical is None else canonical.lifecycle,
        sandbox_opened_count=reconciliation.sandbox.opened_count,
        sandbox_closed_count=reconciliation.sandbox.closed_count,
        canonical_opened_count=(None if canonical is None else canonical.opened_count),
        canonical_closed_count=(None if canonical is None else canonical.closed_count),
        differences=reconciliation.differences,
        canonical_evidence_hashes=reconciliation.canonical_evidence_hashes,
    )
