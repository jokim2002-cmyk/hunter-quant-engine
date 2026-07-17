from __future__ import annotations

from copy import deepcopy

import pytest

from src.multi_strategy.approval import (
    PackageApprovalError,
    approve_review_request,
    build_review_request,
    verify_approval,
)


def package_metadata() -> dict:
    return {
        "strategy_id": "demo.smc",
        "version": "1.0.0",
        "display_name": "Demo SMC",
        "implementation_key": "hqe.reviewed.demo_smc_v1",
        "package_hash": "a" * 64,
        "manifest_hash": "b" * 64,
        "source_code": "must never execute",
    }


def quarantine_record() -> dict:
    return {
        "status": "QUARANTINED",
        "package_hash": "a" * 64,
        "manifest_hash": "b" * 64,
        "quarantine_id": "Q-001",
    }


def request() -> dict:
    return build_review_request(
        package_metadata(),
        quarantine_record(),
        requested_by="review-requester",
        requested_at_utc="2026-07-17T00:00:00Z",
    )


def approval() -> dict:
    return approve_review_request(
        request(),
        approved_by="reviewer",
        decided_at_utc="2026-07-17T00:01:00Z",
        review_note="Metadata reviewed.",
    )


def test_review_request_is_deterministic_and_disabled():
    first = request()
    second = request()
    assert first == second
    assert first["request_status"] == "PENDING_REVIEW"
    assert all(value is False for value in first["controls"].values())


def test_review_request_rejects_non_quarantined_package():
    record = quarantine_record()
    record["status"] = "DISCOVERED"
    with pytest.raises(PackageApprovalError, match="QUARANTINED"):
        build_review_request(
            package_metadata(),
            record,
            requested_by="operator",
            requested_at_utc="2026-07-17T00:00:00Z",
        )


def test_review_request_rejects_quarantine_hash_mismatch():
    record = quarantine_record()
    record["package_hash"] = "c" * 64
    with pytest.raises(PackageApprovalError, match="package_hash"):
        build_review_request(
            package_metadata(),
            record,
            requested_by="operator",
            requested_at_utc="2026-07-17T00:00:00Z",
        )


def test_approval_keeps_all_controls_disabled():
    record = approval()
    assert record["decision"] == "APPROVED"
    assert all(value is False for value in record["controls"].values())


def test_approval_rejects_tampered_review_request():
    tampered = request()
    tampered["package_hash"] = "f" * 64
    with pytest.raises(PackageApprovalError, match="request_hash"):
        approve_review_request(
            tampered,
            approved_by="reviewer",
            decided_at_utc="2026-07-17T00:01:00Z",
        )


def test_verify_rejects_unreviewed_implementation_key():
    with pytest.raises(PackageApprovalError, match="allowlist"):
        verify_approval(
            approval(),
            package_metadata(),
            allowed_implementation_keys={"hqe.reviewed.other_v1"},
        )


def test_verify_rejects_tampered_approval():
    tampered = deepcopy(approval())
    tampered["decision"] = "REJECTED"
    with pytest.raises(PackageApprovalError, match="approval_hash"):
        verify_approval(
            tampered,
            package_metadata(),
            allowed_implementation_keys={
                "hqe.reviewed.demo_smc_v1"
            },
        )
