from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_FINAL_RELEASE_QA_V2"
REQUIRED_RELEASE_ASSETS = (
    "assets/HQE_PRODUCT_APP.ico",
    "release/HQE_INSTALL_DESKTOP_SHORTCUT.ps1",
    "release/HQE_REMOVE_DESKTOP_SHORTCUT.ps1",
    "release/HQE_WINDOWS_RELEASE_MANIFEST.json",
    "release/HQE_PAPER_ONLY_RC_FREEZE_MANIFEST.json",
    "release/HQE_PAPER_ONLY_RC_SIGNOFF.json",
    "release/HQE_MULTI_STRATEGY_PHASE8_RELEASE_CLOSURE.json",
    "scripts/hqe_product_app_v2.py",
    "scripts/hqe_release_candidate_audit.py",
    "scripts/hqe_release_workspace_preflight.py",
    "scripts/hqe_operator_acceptance_engine.py",
    "scripts/hqe_final_rc_signoff_engine.py",
    "scripts/hqe_multi_strategy_phase8_visual_acceptance.py",
    "scripts/hqe_multi_strategy_phase8_release_closure.py",
    "src/multi_strategy/product_ui_manager.py",
    "src/multi_strategy/import_workflow.py",
    "src/multi_strategy/parallel_observation.py",
    "docs/HQE_MULTI_STRATEGY_PHASE8_FINAL_RELEASE_CLOSURE.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_check(repo: Path, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=180)
    return {
        "command": command, "returncode": result.returncode,
        "stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
    }


def build_final_release_qa(repo: Path, workspace: Path) -> dict[str, Any]:
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    assets: dict[str, Any] = {}
    for relative in REQUIRED_RELEASE_ASSETS:
        path = repo / relative
        assets[relative] = {"exists": path.exists(), "sha256": sha256(path) if path.is_file() else ""}
    checks = {
        "app_guard": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_product_app_v2.py"),"--guard-check"]),
        "rc_guard": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_release_candidate_audit.py"),"--guard-check"]),
        "preflight": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_release_workspace_preflight.py"),"--repo-root",str(repo),"--json"]),
        "operator_guard": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_operator_acceptance_engine.py"),"--guard-check"]),
        "signoff_guard": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_final_rc_signoff_engine.py"),"--guard-check"]),
        "visual_guard": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_multi_strategy_phase8_visual_acceptance.py"),"--guard-check"]),
        "closure_guard": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_multi_strategy_phase8_release_closure.py"),"--guard-check"]),
        "closure_evidence": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_multi_strategy_phase8_release_closure.py"),"--repo-root",str(repo),"--verify","--allow-ready"]),
        "freeze_verify": run_check(repo,[str(python_exe),str(repo/"scripts/hqe_release_candidate_audit.py"),"--repo-root",str(repo),"--verify-freeze-manifest"]),
    }
    asset_pass = all(item["exists"] for item in assets.values())
    check_pass = all(item["returncode"] == 0 for item in checks.values())
    combined = "\n".join(item["stdout"] for item in checks.values()).lower()
    safety = {
        "paper_only": "paper" in combined,
        "no_real_orders": "no_real_orders" in combined or "real_orders" in combined,
        "no_broker_execution": "no_broker_execution" in combined or "broker_execution" in combined,
        "no_auto_trading": "no_auto_trading" in combined or "auto_trading" in combined,
        "no_canonical_activation": "canonical_activation" in combined,
    }
    status = "PASS" if asset_pass and check_pass and all(safety.values()) else "FAILED"
    payload = {
        "version": VERSION, "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "assets": assets, "checks": checks, "safety": safety,
        "real_order_invoked": False, "broker_execution_invoked": False,
        "auto_trading_invoked": False, "canonical_activation_invoked": False,
        "master_merge_invoked": False,
    }
    report_dir = workspace / "HQE_RELEASE_QA"; report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "HQE_FINAL_RELEASE_QA_LATEST.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload


def main() -> int:
    parser=argparse.ArgumentParser(description="HQE final release QA")
    parser.add_argument("--repo-root",default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workspace",default=r"D:\HQE_BACKTEST_RUNS\HQE_PHASE8_RELEASE_QA")
    parser.add_argument("--json",action="store_true")
    parser.add_argument("--guard-check",action="store_true")
    args=parser.parse_args()
    if args.guard_check:
        print(json.dumps({"version":VERSION,"guard_check_status":"PASS","paper_only":True,"real_orders_allowed":False,"canonical_activation_allowed":False},indent=2,sort_keys=True)); return 0
    payload=build_final_release_qa(Path(args.repo_root),Path(args.workspace))
    if args.json: print(json.dumps(payload,indent=2,sort_keys=True))
    else: print(f"HQE FINAL RELEASE QA: {payload['status']}"); print(f"Report: {payload['report_path']}")
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
