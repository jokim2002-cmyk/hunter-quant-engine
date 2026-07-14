from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
STATUS_FILE = "HQE_CURRENT_DAY_RECORDED_REPLAY_STATUS.json"


def _today(now: datetime | date | None = None) -> date:
    if now is None:
        return datetime.now(IST).date()
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=IST).date()
        return now.astimezone(IST).date()
    return now


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def recorded_replay_status(
    workspace: Path,
    *,
    now: datetime | date | None = None,
) -> dict[str, Any]:
    today = _today(now)
    source = workspace / STATUS_FILE
    payload = _read(source)

    result: dict[str, Any] = {
        "ready": False,
        "state": "RECORDED_REPLAY_NOT_AVAILABLE",
        "message": (
            "Current-day recorded replay evidence is not available "
            f"for {today.strftime('%d %b %Y')}."
        ),
        "today": today.isoformat(),
        "today_pretty": today.strftime("%d %b %Y"),
        "trading_date": "",
        "report_path": "",
        "summary_path": "",
        "evaluations_path": "",
        "evaluation_count": 0,
        "accepted_evaluation_count": 0,
        "decision_counts": {},
        "accepted_side_counts": {},
        "signal_generated": False,
        "paper_only": True,
        "data_only": True,
        "recorded_data_replay": True,
        "evaluation_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }
    if payload is None:
        return result

    trading_text = str(payload.get("trading_date", "")).strip()
    try:
        trading_day = date.fromisoformat(trading_text)
    except ValueError:
        trading_day = None

    outputs = payload.get("outputs")
    if not isinstance(outputs, dict):
        outputs = {}
    truth = payload.get("replay_truth")
    if not isinstance(truth, dict):
        truth = {}

    paths = {
        "report_path": Path(str(outputs.get("report_html", "")).strip()),
        "summary_path": Path(str(outputs.get("summary_json", "")).strip()),
        "evaluations_path": Path(
            str(outputs.get("evaluations_csv", "")).strip()
        ),
    }
    result.update(
        {
            "trading_date": trading_text,
            **{key: str(value) for key, value in paths.items()},
            "evaluation_count": int(payload.get("evaluation_count") or 0),
            "accepted_evaluation_count": int(
                payload.get("accepted_evaluation_count") or 0
            ),
            "decision_counts": (
                payload.get("decision_counts")
                if isinstance(payload.get("decision_counts"), dict)
                else {}
            ),
            "accepted_side_counts": (
                payload.get("accepted_side_counts")
                if isinstance(payload.get("accepted_side_counts"), dict)
                else {}
            ),
            "signal_generated": bool(payload.get("signal_generated")),
        }
    )

    if trading_day != today:
        result["state"] = "RECORDED_REPLAY_STALE_BLOCKED"
        result["message"] = (
            "Recorded replay opening is blocked because its date is "
            f"{trading_text or 'unknown'}, not {today.isoformat()}."
        )
        return result

    if str(payload.get("status", "")).upper() != (
        "RECORDED_DATA_REPLAY_EVALUATED"
    ):
        result["state"] = "RECORDED_REPLAY_STATUS_INVALID"
        result["message"] = (
            "Current-day replay status is incomplete and is blocked."
        )
        return result

    safety_ok = all(
        (
            payload.get("real_orders_allowed") is False,
            payload.get("broker_execution_allowed") is False,
            payload.get("auto_trading_allowed") is False,
            payload.get("option_selling_allowed") is False,
            truth.get("paper_trade_created") is False,
            truth.get("position_opened") is False,
            truth.get("pnl_calculated") is False,
            truth.get("historical_execution_claim") is False,
        )
    )
    if not safety_ok:
        result["state"] = "RECORDED_REPLAY_SAFETY_BLOCKED"
        result["message"] = "Recorded replay safety truth is incomplete."
        return result

    if not all(path.is_file() for path in paths.values()):
        result["state"] = "RECORDED_REPLAY_FILES_MISSING"
        result["message"] = (
            "Current-day replay status exists, but evidence files "
            "are missing on this computer."
        )
        return result

    result["ready"] = True
    result["state"] = "RECORDED_REPLAY_READY"
    result["message"] = (
        "Current-day genuine FYERS recorded replay is ready for "
        f"{today.strftime('%d %b %Y')}."
    )
    return result
