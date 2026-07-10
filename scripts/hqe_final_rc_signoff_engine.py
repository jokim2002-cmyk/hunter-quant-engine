from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_FINAL_RC_SIGNOFF_ENGINE_V1"
SIGNOFF_FILE = "release/HQE_PAPER_ONLY_RC_SIGNOFF.json"
ACCEPTANCE_ROOT = "HQE_RELEASE_CENTER/operator_acceptance"

ALLOWED_ACCEPTANCE_DECISIONS = {
    "ACCEPTED_FOR_PAPER_ONLY_RC",
    "ACCEPTED_WITH_REVIEW",
}

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "research_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_profitability_claim": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def latest_acceptance_report(workspace: Path) -> Path | None:
    root = workspace / ACCEPTANCE_ROOT
    candidates = sorted(
        root.glob("ACCEPTANCE_*/HQE_OPERATOR_ACCEPTANCE.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if root.exists() else []
    return candidates[0] if candidates else None


def enabled_execution_flags(payload: Any) -> list[str]:
    forbidden = {
        "real_money_enabled",
        "real_orders_enabled",
        "broker_execution_enabled",
        "auto_trading_enabled",
        "option_selling_enabled",
    }
    findings: list[str] = []

    def walk(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if key in forbidden and item is True:
                    findings.append(path)
                walk(item, path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{prefix}[{index}]")

    walk(payload)
    return sorted(set(findings))


def validate_acceptance_report(
    payload: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    decision = payload.get("decision")
    if not isinstance(decision, dict):
        errors.append("Acceptance decision block is missing.")
        decision_status = ""
    else:
        decision_status = str(decision.get("status", "")).strip()

    if decision_status not in (
        ALLOWED_ACCEPTANCE_DECISIONS | {"BLOCKED"}
    ):
        errors.append(
            "Acceptance decision is missing or unsupported."
        )

    unsafe = enabled_execution_flags(payload)
    if unsafe:
        errors.append(
            "Acceptance evidence contains enabled execution flags: "
            + ", ".join(unsafe)
        )

    failed_count = int(payload.get("failed_count", 0) or 0)
    review_count = int(payload.get("review_count", 0) or 0)
    check_count = int(payload.get("check_count", 0) or 0)

    if check_count <= 0:
        errors.append("Acceptance report contains no checks.")

    if decision_status == "BLOCKED" or failed_count > 0:
        errors.append(
            "Acceptance report is blocked by one or more failures."
        )

    if decision_status == "ACCEPTED_WITH_REVIEW":
        warnings.append(
            f"{review_count} acceptance item(s) require operator review."
        )

    operations = payload.get("operations_executed", {})
    if isinstance(operations, dict):
        executed = [
            key for key, value in operations.items()
            if value is True
        ]
        if executed:
            errors.append(
                "Acceptance dry run unexpectedly executed operations: "
                + ", ".join(executed)
            )

    return {
        "valid_for_signoff": not errors,
        "decision_status": decision_status,
        "errors": errors,
        "warnings": warnings,
        "check_count": check_count,
        "passed_count": int(payload.get("passed_count", 0) or 0),
        "review_count": review_count,
        "failed_count": failed_count,
    }


def signoff_status(decision_status: str) -> str:
    if decision_status == "ACCEPTED_FOR_PAPER_ONLY_RC":
        return "PAPER_ONLY_RC_SIGNED_OFF"
    if decision_status == "ACCEPTED_WITH_REVIEW":
        return "PAPER_ONLY_RC_CONDITIONALLY_SIGNED_OFF"
    raise ValueError(
        "Acceptance decision is not eligible for sign-off."
    )


def create_signoff_manifest(
    repo_root: Path,
    workspace: Path,
    *,
    source_head: str = "",
) -> dict[str, Any]:
    acceptance_path = latest_acceptance_report(workspace)
    if acceptance_path is None:
        raise FileNotFoundError(
            "No operator acceptance report was found."
        )

    acceptance = read_json(acceptance_path)
    validation = validate_acceptance_report(acceptance)
    if not validation["valid_for_signoff"]:
        raise ValueError(
            "Operator acceptance is not eligible for sign-off: "
            + "; ".join(validation["errors"])
        )

    decision_status = validation["decision_status"]
    final_status = signoff_status(decision_status)
    current_head = source_head or git_head(repo_root)

    payload = {
        "schema_version": "1.0",
        "engine_version": VERSION,
        "product": "Hunter Quant Engine",
        "release_version": "0.9.0-paper-rc4",
        "release_scope": "PAPER_DATA_RESEARCH_ONLY",
        "signoff_status": final_status,
        "operator_acceptance_decision": decision_status,
        "operator_acceptance_report": str(
            acceptance_path.resolve()
        ),
        "operator_acceptance_generated_at_utc": str(
            acceptance.get("generated_at_utc", "")
        ),
        "source_head_before_signoff_commit": current_head,
        "signoff_commit_message": (
            "Add final paper-only RC evidence and sign-off"
        ),
        "check_count": validation["check_count"],
        "passed_count": validation["passed_count"],
        "review_count": validation["review_count"],
        "failed_count": validation["failed_count"],
        "review_items_remain": (
            decision_status == "ACCEPTED_WITH_REVIEW"
        ),
        "warnings": validation["warnings"],
        "generated_at_utc": utc_now_text(),
        "release_statement": (
            "HQE is signed off only as a paper/data/research "
            "release candidate. Real trading remains excluded."
        ),
        "safety_lock": dict(SAFETY_LOCK),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "profitability_claim": False,
    }
    target = repo_root / SIGNOFF_FILE
    write_json(target, payload)
    payload["signoff_path"] = str(target)
    return payload


def signoff_snapshot(repo_root: Path) -> dict[str, Any]:
    path = repo_root / SIGNOFF_FILE
    payload = read_json(path)
    return {
        "version": VERSION,
        "signoff_path": str(path),
        "exists": bool(payload),
        "signoff": payload,
        "display_text": (
            f"Paper-only RC sign-off: "
            f"{payload.get('signoff_status', 'NOT_CREATED')}"
        ),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "FINAL_PAPER_ONLY_RC_EVIDENCE_AND_SIGNOFF",
        "new_product_features": False,
        "acceptance_report_required": True,
        "blocked_acceptance_rejected": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE final paper-only RC sign-off engine"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--source-head", default="")
    parser.add_argument("--write-signoff", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.snapshot:
        print(json.dumps(
            signoff_snapshot(repo_root),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.write_signoff:
        if not args.workspace:
            parser.error(
                "--workspace is required with --write-signoff."
            )
        print(json.dumps(
            create_signoff_manifest(
                repo_root,
                Path(args.workspace),
                source_head=args.source_head,
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error("Use --write-signoff, --snapshot or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
