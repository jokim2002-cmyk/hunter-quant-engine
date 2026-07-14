from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from hqe_app_fyers_auth import auth_status_snapshot

MODULE_VERSION = "HQE_PAPER_WATCH_AUTH_READINESS_GATE_V1"
IST = ZoneInfo("Asia/Kolkata")
WORKFLOW_STATUS_FILE = (
    "HQE_AUTOMATIC_DAILY_CURRENT_DAY_WORKFLOW_STATUS.json"
)

TOKEN_PROVEN_STATUSES = {
    "COMPLETE",
    "WAITING_MORE_DATA",
    "WAITING_MARKET_DATA",
    "MARKET_CLOSED_OR_HOLIDAY",
}


def _today(now: datetime | date | None = None) -> date:
    if now is None:
        return datetime.now(IST).date()
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=IST).date()
        return now.astimezone(IST).date()
    return now


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _blocked(
    *,
    state: str,
    message: str,
    workflow: dict[str, Any],
    today: date,
    token_present: bool,
) -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "allowed": False,
        "state": state,
        "message": message,
        "warning_title": "Fyers Token Refresh Required",
        "warning_message": (
            message
            + "\n\nOpen Broker Connect → Fyers Login & Token Refresh. "
            "Fresh market data and Start Paper Watch remain blocked "
            "until today's data-only connection is verified."
        ),
        "broker_card": "Fyers: TOKEN REFRESH REQUIRED",
        "data_card": "AUTH REQUIRED\nNO FRESH DATA",
        "watch_card": "START BLOCKED\nAUTH REQUIRED",
        "watch_card_running": (
            "PROCESS RUNNING\nFRESH DATA BLOCKED"
        ),
        "today": today.isoformat(),
        "workflow_status": str(
            workflow.get("status", "NOT_STARTED")
        ).strip().upper(),
        "workflow_stage": str(
            workflow.get("stage", "")
        ).strip().upper(),
        "workflow_trading_date": str(
            workflow.get("trading_date", "")
        ).strip(),
        "token_present_in_secure_store": token_present,
        "paper_only": True,
        "data_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }


def paper_watch_auth_gate(
    workspace: Path,
    *,
    now: datetime | date | None = None,
    auth_snapshot: dict[str, Any] | None = None,
    workflow_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    today = _today(now)
    auth = (
        auth_snapshot
        if isinstance(auth_snapshot, dict)
        else auth_status_snapshot()
    )
    workflow = (
        workflow_snapshot
        if isinstance(workflow_snapshot, dict)
        else _read_json(workspace / WORKFLOW_STATUS_FILE)
    )

    token_present = bool(auth.get("access_token_present"))
    auth_state = str(auth.get("status", "")).strip().upper()
    workflow_status = str(
        workflow.get("status", "NOT_STARTED")
    ).strip().upper()
    workflow_stage = str(
        workflow.get("stage", "")
    ).strip().upper()
    workflow_day = _parse_date(workflow.get("trading_date"))

    if not token_present or auth_state != "READY":
        return _blocked(
            state="SECURE_TOKEN_MISSING",
            message=(
                "A secure FYERS access token is not available. "
                "Paper Watch cannot start without verified fresh data."
            ),
            workflow=workflow,
            today=today,
            token_present=token_present,
        )

    if workflow_day != today:
        return _blocked(
            state="TOKEN_NOT_VERIFIED_TODAY",
            message=(
                "Today's FYERS data-only connection has not been "
                "verified yet. A stored token is not proof that it is "
                "still valid."
            ),
            workflow=workflow,
            today=today,
            token_present=token_present,
        )

    if workflow_status == "AUTH_REQUIRED":
        return _blocked(
            state="AUTH_REQUIRED",
            message=(
                "FYERS rejected the stored access token during today's "
                f"{workflow_stage or 'DATA'} stage. The token is expired "
                "or invalid."
            ),
            workflow=workflow,
            today=today,
            token_present=token_present,
        )

    error_text = " ".join(
        (
            str(workflow.get("message", "")),
            str(workflow.get("error", "")),
        )
    ).lower()
    if (
        "valid token" in error_text
        or "token expired" in error_text
        or "access token" in error_text
        and workflow_status in {"FAILED_SAFE", "SAFETY_BLOCKED"}
    ):
        return _blocked(
            state="AUTH_FAILURE_DETECTED",
            message=(
                "Today's workflow detected a FYERS authentication "
                "failure. Paper Watch start is blocked."
            ),
            workflow=workflow,
            today=today,
            token_present=token_present,
        )

    if workflow_status == "RUNNING":
        return _blocked(
            state="AUTH_VALIDATION_IN_PROGRESS",
            message=(
                "HQE is validating today's FYERS data-only connection. "
                "Wait for the automatic status check to finish."
            ),
            workflow=workflow,
            today=today,
            token_present=token_present,
        )

    if workflow_status not in TOKEN_PROVEN_STATUSES:
        return _blocked(
            state="TOKEN_NOT_PROVEN",
            message=(
                "Today's FYERS token validity is not proven by a "
                "successful data-only workflow stage."
            ),
            workflow=workflow,
            today=today,
            token_present=token_present,
        )

    return {
        "version": MODULE_VERSION,
        "allowed": True,
        "state": "AUTH_AND_DATA_PATH_VERIFIED",
        "message": (
            "Today's FYERS data-only connection passed the secure "
            "readiness gate."
        ),
        "warning_title": "",
        "warning_message": "",
        "broker_card": "Fyers: DATA-ONLY AUTH VERIFIED",
        "data_card": "CURRENT-DAY DATA PATH VERIFIED",
        "watch_card": "READY TO START",
        "watch_card_running": "RUNNING WITH VERIFIED DATA PATH",
        "today": today.isoformat(),
        "workflow_status": workflow_status,
        "workflow_stage": workflow_stage,
        "workflow_trading_date": (
            workflow_day.isoformat()
            if workflow_day is not None
            else ""
        ),
        "token_present_in_secure_store": token_present,
        "paper_only": True,
        "data_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "guard_check_status": "PASS",
        "fail_closed": True,
        "stored_token_is_not_validity_proof": True,
        "paper_watch_start_requires_current_day_data_auth_proof": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }
