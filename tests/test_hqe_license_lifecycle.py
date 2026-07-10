from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_license_lifecycle.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_signed_license_active_and_machine_bound():
    module = load("license_active")
    secret = "test-license-secret-123456"
    machine_hash = "abc123"
    payload = module.build_license_payload(
        license_id="LIC-001",
        customer_label="Test Customer",
        plan="paper",
        issued_on="2026-07-01",
        expires_on="2027-07-01",
        machine_hash=machine_hash,
    )
    signed = module.issue_signed_license(payload, secret)
    result = module.verify_license_payload(
        signed,
        secret=secret,
        current_date=date(2026, 7, 10),
        current_machine_hash=machine_hash,
    )
    assert result["valid"] is True
    assert result["status"] == "ACTIVE"


def test_expired_license_is_not_valid():
    module = load("license_expired")
    secret = "test-license-secret-123456"
    payload = module.build_license_payload(
        license_id="LIC-002",
        customer_label="Expired Customer",
        plan="trial",
        issued_on="2026-01-01",
        expires_on="2026-01-31",
        machine_hash="machine",
    )
    signed = module.issue_signed_license(payload, secret)
    result = module.verify_license_payload(
        signed,
        secret=secret,
        current_date=date(2026, 7, 10),
        current_machine_hash="machine",
    )
    assert result["valid"] is False
    assert result["status"] == "EXPIRED"


def test_tampered_license_is_rejected():
    module = load("license_tamper")
    secret = "test-license-secret-123456"
    payload = module.build_license_payload(
        license_id="LIC-003",
        customer_label="Test",
        plan="paper",
        issued_on="2026-07-01",
        expires_on="2027-07-01",
        machine_hash="machine",
    )
    signed = module.issue_signed_license(payload, secret)
    signed["plan"] = "PRO"
    result = module.verify_license_payload(
        signed,
        secret=secret,
        current_date=date(2026, 7, 10),
        current_machine_hash="machine",
    )
    assert result["valid"] is False
    assert any(
        "signature" in error.lower()
        for error in result["errors"]
    )


def test_development_mode_does_not_require_license(tmp_path):
    module = load("license_development")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    snapshot = module.license_snapshot(
        repo,
        tmp_path / "workspace",
    )
    assert snapshot["status"] == "DEVELOPMENT_MODE"
    assert snapshot["valid"] is True
    assert snapshot["real_orders_enabled"] is False


def test_license_guard_locks_execution():
    module = load("license_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["integrity_method"] == "HMAC_SHA256_ENV_KEY"
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
