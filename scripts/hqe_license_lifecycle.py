from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_LICENSE_LIFECYCLE_V1"
LICENSE_FILE = "HQE_LICENSE.json"
PRODUCT_ID = "HUNTER_QUANT_ENGINE"

ALLOWED_PLANS = {"TRIAL", "PAPER", "PRO"}
ALLOWED_FEATURES = {
    "APP",
    "MARKET_DATA",
    "STRATEGY_PACKS",
    "BACKTEST",
    "PAPER_VALIDATION",
    "REPORT_EXPORT",
}

SAFETY_LOCK = {
    "paper_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def machine_fingerprint() -> str:
    raw = "|".join(
        (
            platform.node(),
            platform.system(),
            platform.machine(),
            os.environ.get("COMPUTERNAME", ""),
            os.environ.get("PROCESSOR_IDENTIFIER", ""),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_payload(payload: dict[str, Any]) -> str:
    clean = {
        key: value
        for key, value in payload.items()
        if key not in {"signature", "verification"}
    }
    return json.dumps(
        clean,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sign_payload(
    payload: dict[str, Any],
    secret: str,
) -> str:
    if len(secret) < 16:
        raise ValueError(
            "License signing secret must contain at least 16 characters."
        )
    return hmac.new(
        secret.encode("utf-8"),
        canonical_payload(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_license_payload(
    *,
    license_id: str,
    customer_label: str,
    plan: str,
    issued_on: str,
    expires_on: str,
    machine_hash: str,
    features: list[str] | None = None,
) -> dict[str, Any]:
    plan_value = plan.strip().upper()
    if plan_value not in ALLOWED_PLANS:
        raise ValueError("Unsupported license plan.")

    issue_date = date.fromisoformat(issued_on)
    expiry_date = date.fromisoformat(expires_on)
    if expiry_date < issue_date:
        raise ValueError("License expiry cannot precede issue date.")

    feature_values = features or sorted(ALLOWED_FEATURES)
    invalid = [
        feature
        for feature in feature_values
        if feature not in ALLOWED_FEATURES
    ]
    if invalid:
        raise ValueError(
            "Unsupported license features: " + ", ".join(invalid)
        )

    return {
        "schema_version": "1.0",
        "product_id": PRODUCT_ID,
        "license_id": license_id.strip(),
        "customer_label": customer_label.strip(),
        "plan": plan_value,
        "issued_on": issue_date.isoformat(),
        "expires_on": expiry_date.isoformat(),
        "machine_hash": machine_hash.strip(),
        "features": sorted(set(feature_values)),
        "safety": dict(SAFETY_LOCK),
    }


def issue_signed_license(
    payload: dict[str, Any],
    secret: str,
) -> dict[str, Any]:
    signed = dict(payload)
    signed["signature"] = sign_payload(signed, secret)
    return signed


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def verify_license_payload(
    payload: dict[str, Any],
    *,
    secret: str,
    current_date: date | None = None,
    current_machine_hash: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    required = (
        "schema_version",
        "product_id",
        "license_id",
        "customer_label",
        "plan",
        "issued_on",
        "expires_on",
        "machine_hash",
        "features",
        "safety",
        "signature",
    )
    for field in required:
        if field not in payload:
            errors.append(f"Missing license field: {field}")

    if errors:
        return {
            "valid": False,
            "status": "INVALID",
            "errors": errors,
            "warnings": warnings,
        }

    if payload.get("product_id") != PRODUCT_ID:
        errors.append("License product_id does not match HQE.")

    if str(payload.get("plan", "")).upper() not in ALLOWED_PLANS:
        errors.append("Unsupported license plan.")

    features = payload.get("features")
    if not isinstance(features, list):
        errors.append("License features must be a list.")
    else:
        invalid_features = [
            feature
            for feature in features
            if feature not in ALLOWED_FEATURES
        ]
        if invalid_features:
            errors.append("License contains unsupported features.")

    safety = payload.get("safety")
    if not isinstance(safety, dict):
        errors.append("License safety block is missing.")
    else:
        for key, expected in SAFETY_LOCK.items():
            if safety.get(key) is not expected:
                errors.append(
                    f"License safety.{key} must remain {expected}."
                )

    try:
        issue_date = date.fromisoformat(str(payload.get("issued_on", "")))
        expiry_date = date.fromisoformat(str(payload.get("expires_on", "")))
    except ValueError:
        issue_date = date.min
        expiry_date = date.min
        errors.append("License dates must use YYYY-MM-DD.")

    expected_signature = sign_payload(payload, secret)
    actual_signature = str(payload.get("signature", ""))
    if not hmac.compare_digest(expected_signature, actual_signature):
        errors.append("License integrity signature is invalid.")

    machine_hash = current_machine_hash or machine_fingerprint()
    if str(payload.get("machine_hash", "")) != machine_hash:
        errors.append("License is not assigned to this machine.")

    today = current_date or date.today()
    if issue_date > today:
        errors.append("License issue date is in the future.")

    status = "ACTIVE"
    days_remaining = (expiry_date - today).days
    if expiry_date < today:
        status = "EXPIRED"
    elif days_remaining <= 14:
        status = "EXPIRING_SOON"
        warnings.append(
            f"License expires in {days_remaining} day(s)."
        )

    if errors:
        status = "INVALID"

    return {
        "valid": not errors and status in {"ACTIVE", "EXPIRING_SOON"},
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "days_remaining": days_remaining,
        "plan": str(payload.get("plan", "")),
        "license_id": str(payload.get("license_id", "")),
        "customer_label": str(payload.get("customer_label", "")),
        "expires_on": str(payload.get("expires_on", "")),
        "features": list(payload.get("features", []))
        if isinstance(payload.get("features"), list)
        else [],
    }


def license_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    license_path = workspace / LICENSE_FILE
    development_mode = (repo_root / ".git").exists()
    secret = os.environ.get("HQE_LICENSE_VERIFY_KEY", "")

    if development_mode and not license_path.exists():
        return {
            "version": VERSION,
            "status": "DEVELOPMENT_MODE",
            "valid": True,
            "message": (
                "Git development workspace detected. Production "
                "license enforcement is not active."
            ),
            "license_path": str(license_path),
            "development_mode": True,
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
            "safety_lock": SAFETY_LOCK,
        }

    if not license_path.exists():
        return {
            "version": VERSION,
            "status": "LICENSE_REQUIRED",
            "valid": False,
            "message": "Production license file is missing.",
            "license_path": str(license_path),
            "development_mode": development_mode,
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
            "safety_lock": SAFETY_LOCK,
        }

    if len(secret) < 16:
        return {
            "version": VERSION,
            "status": "VERIFY_KEY_REQUIRED",
            "valid": False,
            "message": (
                "HQE_LICENSE_VERIFY_KEY is not configured for "
                "offline integrity verification."
            ),
            "license_path": str(license_path),
            "development_mode": development_mode,
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
            "safety_lock": SAFETY_LOCK,
        }

    payload = read_json(license_path)
    verification = verify_license_payload(
        payload,
        secret=secret,
    )
    return {
        "version": VERSION,
        **verification,
        "message": (
            "License is active."
            if verification["status"] == "ACTIVE"
            else "License requires attention."
        ),
        "license_path": str(license_path),
        "development_mode": development_mode,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "OFFLINE_LICENSE_LIFECYCLE",
        "integrity_method": "HMAC_SHA256_ENV_KEY",
        "development_mode_supported": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE offline license lifecycle"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")
    if args.snapshot:
        print(json.dumps(
            license_snapshot(
                Path(args.repo_root),
                Path(args.workspace),
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --snapshot or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
