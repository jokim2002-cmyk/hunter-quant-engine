from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

import pytest

from src.multi_strategy.lifecycle_reconciliation import (
    LifecycleReconciliationError,
    LifecycleReconciliationStatus,
    LifecycleSemanticObservation,
    ReadOnlyLifecycleReconciliation,
)
from src.multi_strategy.lifecycle_reconciliation_view import (
    ReadOnlyLifecycleReconciliationView,
    build_reconciliation_view,
)


def observation(lifecycle="FLAT", opened=1, closed=1):
    return LifecycleSemanticObservation(
        lifecycle=lifecycle,
        opened_count=opened,
        closed_count=closed,
        unmatched_open_count=opened - closed,
        option_side="CE_BUY" if lifecycle == "OPEN" else "",
        option_symbol="NIFTY_PHASE4L_CE" if lifecycle == "OPEN" else "",
        quantity=75 if lifecycle == "OPEN" else 0,
        entry=100.0 if lifecycle == "OPEN" else None,
    )


def reconciliation(status=LifecycleReconciliationStatus.MATCH_FLAT):
    if status is LifecycleReconciliationStatus.MATCH_OPEN:
        sandbox = observation("OPEN", 1, 0)
        canonical = observation("OPEN", 1, 0)
        differences = ()
    elif status is LifecycleReconciliationStatus.MATCH_FLAT:
        sandbox = observation()
        canonical = observation()
        differences = ()
    else:
        sandbox = observation("OPEN", 1, 0)
        canonical = observation()
        differences = ("lifecycle differs",)
    return ReadOnlyLifecycleReconciliation(
        status=status,
        strategy_id="hqe_current_smc_compatibility",
        strategy_version="1.0.0",
        selection_hash="selection-hash",
        sandbox_bundle_hash="bundle-hash",
        canonical_plan_hash="plan-hash",
        sandbox=sandbox,
        canonical=canonical,
        canonical_evidence_hashes={"state": "abc", "ledger": "def"},
        differences=differences,
    )


def test_flat_match_view_recommendation():
    view = build_reconciliation_view(reconciliation())
    assert view.recommendation == "MATCH_FLAT_READ_ONLY"
    assert view.matched is True


def test_open_match_view_keeps_switch_blocked():
    view = build_reconciliation_view(
        reconciliation(LifecycleReconciliationStatus.MATCH_OPEN)
    )
    assert view.recommendation == "MATCH_OPEN_READ_ONLY_SWITCH_BLOCKED"
    assert view.strategy_switch_enabled is False


def test_divergence_view_requires_review():
    view = build_reconciliation_view(
        reconciliation(LifecycleReconciliationStatus.DIVERGED_LIFECYCLE)
    )
    assert view.recommendation == "REVIEW_REQUIRED_READ_ONLY"
    assert view.matched is False


def test_view_all_mutating_controls_are_disabled():
    payload = build_reconciliation_view(reconciliation()).to_dict()
    for key in (
        "strategy_switch_enabled",
        "lifecycle_write_enabled",
        "runtime_cutover_enabled",
        "broker_execution_enabled",
        "real_money_enabled",
    ):
        assert payload[key] is False


def test_view_hash_is_deterministic():
    first = build_reconciliation_view(reconciliation())
    second = build_reconciliation_view(reconciliation())
    assert first.view_hash == second.view_hash


def test_view_copies_sorted_evidence_hashes():
    view = build_reconciliation_view(reconciliation())
    assert list(view.canonical_evidence_hashes) == ["ledger", "state"]
    assert isinstance(view.canonical_evidence_hashes, MappingProxyType)


def test_view_serialization_contains_reconciliation_hash():
    result = reconciliation()
    payload = build_reconciliation_view(result).to_dict()
    assert payload["reconciliation_hash"] == result.reconciliation_hash
    assert payload["view_hash"]


def test_view_rejects_write_control():
    view = build_reconciliation_view(reconciliation())
    with pytest.raises(LifecycleReconciliationError, match="mutating controls"):
        replace(view, lifecycle_write_enabled=True)


def test_view_rejects_non_read_only_mode():
    view = build_reconciliation_view(reconciliation())
    with pytest.raises(LifecycleReconciliationError, match="read-only"):
        replace(view, read_only=False)
