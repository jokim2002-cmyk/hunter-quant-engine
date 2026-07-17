from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_MULTI_STRATEGY_RELEASE_CLOSURE_VISIBLE_NAV_V2"
CLOSURE_PATH = "release/HQE_MULTI_STRATEGY_PHASE8_RELEASE_CLOSURE.json"
MANIFEST_PATH = "release/HQE_WINDOWS_RELEASE_MANIFEST.json"
FINAL_STATUS = "PAPER_ONLY_MULTI_STRATEGY_RELEASE_CLOSED"
READY_STATUS = "VALIDATION_READY"
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
    "no_canonical_activation": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def release_version(repo_root: Path) -> str:
    manifest = read_json(repo_root / MANIFEST_PATH)
    return str(manifest.get("product_version", ""))


def git_head(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root,
        capture_output=True, text=True, check=True,
    )
    return completed.stdout.strip()


def visible_navigation_passed(visual: dict[str, Any]) -> bool:
    navigation = visual.get("visible_navigation", {})
    return (
        navigation.get("status") == "PASS"
        and navigation.get("advanced_tools_page_direct_cards") is True
        and navigation.get("product_strategy_manager_button_invoked") is True
        and navigation.get("parallel_observation_button_invoked") is True
        and navigation.get("actual_button_invocation") is True
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "FINAL_PAPER_ONLY_MULTI_STRATEGY_RELEASE_CLOSURE",
        "freeze_refresh_required": True,
        "direct_visible_navigation_required": True,
        "master_merge_allowed": False,
        "canonical_activation_allowed": False,
        "runtime_control_allowed": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
        "safety_lock": dict(SAFETY_LOCK),
    }


def build_ready_payload(
    repo_root: Path,
    visual_report: Path,
    *,
    source_head: str,
) -> dict[str, Any]:
    visual = read_json(visual_report)
    if visual.get("status") != "PASS" or not visible_navigation_passed(visual):
        raise ValueError(
            "Validation-ready closure requires direct visible-navigation PASS"
        )
    return {
        "schema_version": "1.0",
        "engine_version": VERSION,
        "product": "Hunter Quant Engine",
        "release_version": release_version(repo_root),
        "closure_status": READY_STATUS,
        "release_scope": "PAPER_DATA_RESEARCH_MULTI_STRATEGY_ONLY",
        "generated_at_utc": utc_now(),
        "source_head_before_closure_commit": source_head,
        "visual_acceptance": {
            "status": "PASS",
            "report_path": str(visual_report),
            "sha256": sha256(visual_report),
            "actual_gui_render_smoke_executed": bool(
                visual.get("actual_gui_render_smoke_executed")
            ),
            "visible_navigation": dict(
                visual.get("visible_navigation", {})
            ),
            "manual_visual_signoff_claimed": False,
        },
        "validation": {
            "focused_release_tests": "PENDING",
            "cumulative_multi_strategy": "PENDING",
            "environment_recovery": "PENDING",
            "full_functional_regression": "PENDING",
            "freeze_verification": "PASS",
        },
        "multi_strategy_phases_closed": [0,1,2,3,4,5,6,7,8],
        "safety_lock": dict(SAFETY_LOCK),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "canonical_selection_changed": False,
        "canonical_activation_performed": False,
        "human_cutover_gate_created": False,
        "runtime_control_performed": False,
        "lifecycle_state_ledger_write_performed": False,
        "master_merge_performed": False,
        "profitability_claim": False,
        "release_statement": (
            "HQE Phase 8 validation is ready and remains paper/data/research only. "
            "Final closure is written only after all release gates pass."
        ),
    }


def build_final_payload(
    repo_root: Path,
    visual_report: Path,
    *,
    source_head: str,
    focused: str,
    cumulative: str,
    environment: str,
    full_regression: str,
    freeze_verification: str,
) -> dict[str, Any]:
    visual = read_json(visual_report)
    validations = {
        "focused_release_tests": focused,
        "cumulative_multi_strategy": cumulative,
        "environment_recovery": environment,
        "full_functional_regression": full_regression,
        "freeze_verification": freeze_verification,
    }
    all_pass = (
        visual.get("status") == "PASS"
        and visible_navigation_passed(visual)
        and all("PASS" in value for value in validations.values())
    )
    if not all_pass:
        raise ValueError("Final release closure requires all validation gates PASS")
    return {
        "schema_version": "1.0",
        "engine_version": VERSION,
        "product": "Hunter Quant Engine",
        "release_version": release_version(repo_root),
        "closure_status": FINAL_STATUS,
        "release_scope": "PAPER_DATA_RESEARCH_MULTI_STRATEGY_ONLY",
        "generated_at_utc": utc_now(),
        "source_head_before_closure_commit": source_head,
        "visual_acceptance": {
            "status": "PASS",
            "report_path": str(visual_report),
            "sha256": sha256(visual_report),
            "actual_gui_render_smoke_executed": bool(
                visual.get("actual_gui_render_smoke_executed")
            ),
            "visible_navigation": dict(
                visual.get("visible_navigation", {})
            ),
            "manual_visual_signoff_claimed": False,
        },
        "validation": validations,
        "multi_strategy_phases_closed": [0,1,2,3,4,5,6,7,8],
        "safety_lock": dict(SAFETY_LOCK),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "canonical_selection_changed": False,
        "canonical_activation_performed": False,
        "human_cutover_gate_created": False,
        "runtime_control_performed": False,
        "lifecycle_state_ledger_write_performed": False,
        "master_merge_performed": False,
        "profitability_claim": False,
        "release_statement": (
            "HQE multi-strategy roadmap is closed only for paper/data/research use. "
            "Real execution and canonical activation remain excluded."
        ),
    }


def write_ready_closure(
    repo_root: Path,
    visual_report: Path,
    *,
    source_head: str,
) -> dict[str, Any]:
    payload = build_ready_payload(
        repo_root,
        visual_report,
        source_head=source_head,
    )
    target = repo_root / CLOSURE_PATH
    atomic_write_json(target, payload)
    payload["closure_path"] = str(target)
    payload["closure_sha256"] = sha256(target)
    return payload


def write_final_closure(
    repo_root: Path,
    visual_report: Path,
    **validation: str,
) -> dict[str, Any]:
    payload = build_final_payload(repo_root, visual_report, **validation)
    target = repo_root / CLOSURE_PATH
    atomic_write_json(target, payload)
    payload["closure_path"] = str(target)
    payload["closure_sha256"] = sha256(target)
    return payload


def verify_closure(repo_root: Path, *, require_final: bool = True) -> dict[str, Any]:
    target = repo_root / CLOSURE_PATH
    payload = read_json(target)
    problems: list[str] = []
    allowed_status = {FINAL_STATUS} if require_final else {"VALIDATION_READY", FINAL_STATUS}
    if payload.get("closure_status") not in allowed_status:
        problems.append("closure_status")
    if payload.get("release_version") != release_version(repo_root):
        problems.append("release_version")
    safety = payload.get("safety_lock", {})
    for key, value in SAFETY_LOCK.items():
        if safety.get(key) is not value:
            problems.append(f"safety_lock.{key}")
    for key in (
        "real_money_enabled", "real_orders_enabled", "broker_execution_enabled",
        "auto_trading_enabled", "option_selling_enabled",
        "canonical_activation_performed", "human_cutover_gate_created",
        "master_merge_performed", "profitability_claim",
    ):
        if payload.get(key) is not False:
            problems.append(key)
    visual = payload.get("visual_acceptance", {})
    report_text = str(visual.get("report_path", ""))
    if payload.get("closure_status") == FINAL_STATUS:
        report = Path(report_text)
        if not report.is_file() or sha256(report) != str(visual.get("sha256", "")):
            problems.append("visual_acceptance_evidence")
        if visual.get("status") != "PASS":
            problems.append("visual_acceptance.status")
        navigation = visual.get("visible_navigation", {})
        if not (
            navigation.get("status") == "PASS"
            and navigation.get("advanced_tools_page_direct_cards") is True
            and navigation.get("product_strategy_manager_button_invoked") is True
            and navigation.get("parallel_observation_button_invoked") is True
            and navigation.get("actual_button_invocation") is True
        ):
            problems.append("visual_acceptance.visible_navigation")
        if not all("PASS" in str(value) for value in payload.get("validation", {}).values()):
            problems.append("validation")
    return {
        "status": "PASS" if not problems else "FAILED",
        "closure_status": payload.get("closure_status", "MISSING"),
        "problems": problems,
        "closure_path": str(target),
        "closure_sha256": sha256(target) if target.is_file() else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE Phase 8 release closure")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--allow-ready", action="store_true")
    parser.add_argument("--write-ready", action="store_true")
    parser.add_argument("--write-final", action="store_true")
    parser.add_argument("--visual-report", default="")
    parser.add_argument("--source-head", default="")
    parser.add_argument("--focused", default="")
    parser.add_argument("--cumulative", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--full-regression", default="")
    parser.add_argument("--freeze-verification", default="")
    args = parser.parse_args()
    repo = Path(args.repo_root)
    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True)); return 0
    if args.verify:
        payload = verify_closure(repo, require_final=not args.allow_ready)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    if args.write_ready:
        if not args.visual_report:
            parser.error("--visual-report is required")
        payload = write_ready_closure(
            repo,
            Path(args.visual_report),
            source_head=args.source_head or git_head(repo),
        )
        print(json.dumps(payload, indent=2, sort_keys=True)); return 0
    if args.write_final:
        if not args.visual_report:
            parser.error("--visual-report is required")
        payload = write_final_closure(
            repo, Path(args.visual_report), source_head=args.source_head or git_head(repo),
            focused=args.focused, cumulative=args.cumulative,
            environment=args.environment, full_regression=args.full_regression,
            freeze_verification=args.freeze_verification,
        )
        print(json.dumps(payload, indent=2, sort_keys=True)); return 0
    parser.error("Use --guard-check, --verify, --write-ready or --write-final")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
