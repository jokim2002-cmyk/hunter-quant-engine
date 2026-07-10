from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

VERSION = "HQE_FYERS_CREDENTIAL_VALIDATION_V1"
OUTPUT_FILENAME = "HQE_FYERS_CREDENTIAL_VALIDATION.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def fingerprint(value: Optional[str]) -> str:
    if value is None:
        return "MISSING"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12].upper()


def inspect_secret(name: str, value: Optional[str]) -> Dict[str, Any]:
    if value is None:
        return {
            "name": name,
            "present": False,
            "length": 0,
            "fingerprint": "MISSING",
            "leading_or_trailing_whitespace": False,
            "wrapped_in_quotes": False,
            "contains_newline": False,
            "contains_tab": False,
            "hygiene_status": "MISSING",
        }

    stripped = value.strip()
    wrapped = (
        len(stripped) >= 2
        and stripped[0] == stripped[-1]
        and stripped[0] in {"'", '"'}
    )
    edge_whitespace = value != stripped
    contains_newline = "\n" in value or "\r" in value
    contains_tab = "\t" in value

    issues = []
    if edge_whitespace:
        issues.append("EDGE_WHITESPACE")
    if wrapped:
        issues.append("WRAPPED_IN_QUOTES")
    if contains_newline:
        issues.append("NEWLINE_PRESENT")
    if contains_tab:
        issues.append("TAB_PRESENT")

    return {
        "name": name,
        "present": bool(value),
        "length": len(value),
        "fingerprint": fingerprint(value),
        "leading_or_trailing_whitespace": edge_whitespace,
        "wrapped_in_quotes": wrapped,
        "contains_newline": contains_newline,
        "contains_tab": contains_tab,
        "hygiene_status": "PASS" if not issues else "SUSPECT_" + "_".join(issues),
    }


def latest_auth_evidence(workspace: Path) -> Dict[str, Any]:
    diagnostic = read_json(workspace / "HQE_FYERS_LIVE_FETCH_DIAGNOSTIC.json")
    response = (
        diagnostic.get("fetch_status_after", {})
        .get("history_result", {})
        .get("response_redacted", {})
    )

    if not response:
        status = read_json(
            workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
        )
        response = (
            status.get("history_result", {})
            .get("response_redacted", {})
        )

    return {
        "code": response.get("code"),
        "message": str(response.get("message") or ""),
        "status": str(response.get("s") or ""),
    }


def launcher_alignment(repo: Path) -> Dict[str, Any]:
    paths = [
        repo / "OPEN_HQE_APP_V2.cmd",
        repo / "OPEN_HQE_OPERATOR_DASHBOARD.cmd",
    ]
    results = []

    for path in paths:
        text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
        results.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "mentions_client_id": "FYERS_CLIENT_ID" in text,
                "mentions_access_token": "FYERS_ACCESS_TOKEN" in text,
            }
        )

    return {
        "expected_source": "CURRENT_PROCESS_ENVIRONMENT",
        "launchers": results,
        "launcher_embeds_secret_names": any(
            item["mentions_client_id"] or item["mentions_access_token"]
            for item in results
        ),
    }


def classify(
    client: Dict[str, Any],
    token: Dict[str, Any],
    auth: Dict[str, Any],
) -> Dict[str, str]:
    if not client["present"] or not token["present"]:
        return {
            "auth_status": "CREDENTIALS_MISSING",
            "recommendation": "SET_FYERS_CLIENT_ID_AND_ACCESS_TOKEN_IN_CURRENT_SESSION",
        }

    if client["hygiene_status"] != "PASS" or token["hygiene_status"] != "PASS":
        return {
            "auth_status": "CREDENTIAL_FORMAT_SUSPECT",
            "recommendation": "REMOVE_QUOTES_WHITESPACE_OR_NEWLINES_AND_REVALIDATE",
        }

    message = str(auth.get("message") or "").lower()
    if auth.get("code") == -16 or "authenticate" in message:
        return {
            "auth_status": "AUTH_FAILED_CODE_-16",
            "recommendation": "REFRESH_FYERS_ACCESS_TOKEN_AND_REVALIDATE",
        }

    return {
        "auth_status": "CREDENTIALS_PRESENT_READY_FOR_REVALIDATION",
        "recommendation": "RUN_ONE_SHOT_LIVE_FETCH_DIAGNOSTIC",
    }


def run_fetch_revalidation(repo: Path, workspace: Path) -> Dict[str, Any]:
    command = [
        str(repo / ".venv" / "Scripts" / "python.exe"),
        str(repo / "scripts" / "hqe_fyers_live_fetch_diagnostic.py"),
        "--workspace",
        str(workspace),
        "--repo-root",
        str(repo),
        "--execute-fetch",
    ]
    completed = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=180,
    )
    payload = read_json(workspace / "HQE_FYERS_LIVE_FETCH_DIAGNOSTIC.json")
    return {
        "executed": True,
        "returncode": completed.returncode,
        "decision": payload.get("decision", "UNKNOWN"),
        "recommendation": payload.get("recommendation", "UNKNOWN"),
    }


def build_status(
    repo: Path,
    workspace: Path,
    *,
    run_revalidation: bool = False,
) -> Dict[str, Any]:
    client = inspect_secret("FYERS_CLIENT_ID", os.environ.get("FYERS_CLIENT_ID"))
    token = inspect_secret("FYERS_ACCESS_TOKEN", os.environ.get("FYERS_ACCESS_TOKEN"))
    auth = latest_auth_evidence(workspace)
    result = classify(client, token, auth)

    revalidation = {
        "executed": False,
        "decision": "NOT_REQUESTED",
        "recommendation": "USE_RUN_FETCH_REVALIDATION_AFTER_TOKEN_REFRESH",
    }
    if run_revalidation and client["present"] and token["present"]:
        revalidation = run_fetch_revalidation(repo, workspace)
        auth = latest_auth_evidence(workspace)
        result = classify(client, token, auth)
        if (
            revalidation.get("returncode") == 0
            and revalidation.get("decision") == "LIVE_FETCH_UPDATED_CANDLE_DATA"
        ):
            result = {
                "auth_status": "AUTH_OK_CODE_200",
                "recommendation": "START_OR_RESTART_PAPER_WATCH_WITH_CURRENT_TOKEN",
            }

    return {
        "version": VERSION,
        "generated_at_utc": utc_now(),
        "repo": str(repo),
        "workspace": str(workspace),
        "auth_status": result["auth_status"],
        "recommendation": result["recommendation"],
        "client_id": client,
        "access_token": token,
        "latest_auth_evidence": auth,
        "launcher_alignment": launcher_alignment(repo),
        "revalidation": revalidation,
        "secrets_redacted": True,
        "paper_only": True,
        "data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE Fyers credential validation")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repo-root")
    parser.add_argument("--run-fetch-revalidation", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    workspace = Path(args.workspace)

    if not repo.exists():
        raise SystemExit(f"Repo not found: {repo}")
    if not workspace.exists():
        raise SystemExit(f"Workspace not found: {workspace}")

    payload = build_status(
        repo,
        workspace,
        run_revalidation=args.run_fetch_revalidation,
    )

    if not args.no_write:
        atomic_write_json(workspace / OUTPUT_FILENAME, payload)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
