from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time as time_module
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from hqe_app_fyers_auth import (
    apply_stored_fyers_environment,
    auth_status_snapshot,
)
from hqe_current_day_recorded_replay_evaluation import (
    run_live_data_only as run_recorded_replay,
)
from hqe_fyers_option_chain_data_only import (
    DEFAULT_SYMBOL,
    SAFETY_LOCK,
    run_live_data_only as run_option_chain,
)
from hqe_fyers_selected_option_history_data_only import (
    run_live_data_only as run_selected_history,
)

MODULE_VERSION = "HQE_AUTOMATIC_DAILY_CURRENT_DAY_WORKFLOW_V1"
IST = ZoneInfo("Asia/Kolkata")
MARKET_START = time(9, 15)
MARKET_END = time(15, 35)
DEFAULT_INTERVAL_SECONDS = 300
STATUS_FILE = "HQE_AUTOMATIC_DAILY_CURRENT_DAY_WORKFLOW_STATUS.json"

AUTOMATIC_SAFETY = {
    **SAFETY_LOCK,
    "automatic_data_workflow": True,
    "recorded_data_evaluation_only": True,
    "no_position_opening": True,
    "no_pnl_calculation": True,
}

_RUN_LOCK = threading.Lock()
_WORKERS: dict[str, threading.Thread] = {}


class WorkflowDependencies:
    """Small immutable-style dependency container.

    A plain class is used instead of dataclass because HQE tests load
    script modules directly with importlib without first registering
    them in sys.modules. Python 3.12 dataclass annotation inspection
    can fail in that direct-loader mode.
    """

    __slots__ = (
        "auth_status",
        "apply_auth",
        "option_chain",
        "selected_history",
        "recorded_replay",
    )

    def __init__(
        self,
        *,
        auth_status: Callable[[], dict[str, Any]],
        apply_auth: Callable[..., dict[str, Any]],
        option_chain: Callable[..., dict[str, Any]],
        selected_history: Callable[..., dict[str, Any]],
        recorded_replay: Callable[..., dict[str, Any]],
    ) -> None:
        self.auth_status = auth_status
        self.apply_auth = apply_auth
        self.option_chain = option_chain
        self.selected_history = selected_history
        self.recorded_replay = recorded_replay


def default_dependencies() -> WorkflowDependencies:
    return WorkflowDependencies(
        auth_status=auth_status_snapshot,
        apply_auth=apply_stored_fyers_environment,
        option_chain=run_option_chain,
        selected_history=run_selected_history,
        recorded_replay=run_recorded_replay,
    )


def ist_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(IST)
    if now.tzinfo is None:
        return now.replace(tzinfo=IST)
    return now.astimezone(IST)


def market_phase(now: datetime | None = None) -> str:
    current = ist_now(now)
    if current.weekday() >= 5:
        return "WEEKEND"
    if current.time() < MARKET_START:
        return "PRE_MARKET"
    if current.time() <= MARKET_END:
        return "MARKET_ACTIVE"
    return "POST_MARKET"


def status_path(workspace: Path) -> Path:
    return workspace / STATUS_FILE


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            default=str,
        )
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def status_snapshot(workspace: Path) -> dict[str, Any]:
    source = status_path(workspace)
    payload = _read_json(source)
    if payload:
        return payload
    return {
        "version": MODULE_VERSION,
        "status": "NOT_STARTED",
        "message": "Automatic daily current-day workflow has not started.",
        "status_path": str(source),
        "paper_only": True,
        "data_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }


def _base_payload(
    *,
    workspace: Path,
    current: datetime,
    status: str,
    message: str,
    stage: str,
) -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "status": status,
        "message": message,
        "stage": stage,
        "market_phase": market_phase(current),
        "trading_date": current.date().isoformat(),
        "local_time_ist": current.isoformat(timespec="seconds"),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "workspace": str(workspace),
        "status_path": str(status_path(workspace)),
        "secret_values": "REDACTED",
        "paper_only": True,
        "data_only": True,
        "recorded_data_replay": True,
        "evaluation_only": True,
        "paper_trade_created": False,
        "position_opened": False,
        "pnl_calculated": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "profitability_claim": False,
        "safety_lock": AUTOMATIC_SAFETY,
    }


def _write_status(
    workspace: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _atomic_json(status_path(workspace), payload)
    return payload


def _error_status(
    *,
    workspace: Path,
    current: datetime,
    stage: str,
    exc: BaseException,
) -> dict[str, Any]:
    text = str(exc).strip()
    lowered = text.lower()
    phase = market_phase(current)

    if (
        "valid token" in lowered
        or "token expired" in lowered
        or "access token" in lowered
        or "auth" in lowered and "required" in lowered
    ):
        status = "AUTH_REQUIRED"
        message = (
            "FYERS secure token needs refresh from Broker Connect. "
            "Automatic workflow stopped safely for this cycle."
        )
    elif (
        "not enough nifty" in lowered
        or "required=21" in lowered
        or "enough valid 5-minute rows" in lowered
    ):
        status = "WAITING_MORE_DATA"
        message = (
            "Current-day market history is genuine but does not yet "
            "contain enough 5-minute bars for SMC replay."
        )
    elif (
        "returned no historical candles" in lowered
        or "returned no nifty candles" in lowered
        or "no historical candles" in lowered
        or "no nifty candles" in lowered
        or "no same-expiry" in lowered
        or "option-chain" in lowered
        or "option chain" in lowered
    ):
        if phase == "POST_MARKET":
            status = "MARKET_CLOSED_OR_HOLIDAY"
            message = (
                "No complete current-day market dataset was available "
                "after market hours. The day may be a holiday or data "
                "may still be unavailable."
            )
        else:
            status = "WAITING_MARKET_DATA"
            message = (
                "Current-day FYERS data is not complete yet. "
                "Automatic workflow will retry."
            )
    else:
        status = "FAILED_SAFE"
        message = (
            f"Automatic daily workflow failed safely at {stage}: "
            f"{type(exc).__name__}: {text[:300]}"
        )

    return _write_status(
        workspace,
        {
            **_base_payload(
                workspace=workspace,
                current=current,
                status=status,
                message=message,
                stage=stage,
            ),
            "error_type": type(exc).__name__,
            "error": text[:500],
            "next_retry_seconds": (
                300
                if status in {
                    "WAITING_MORE_DATA",
                    "WAITING_MARKET_DATA",
                    "AUTH_REQUIRED",
                }
                else 900
            ),
        },
    )


def _safe_count(
    payload: dict[str, Any],
    *keys: str,
) -> int:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return 0
        value = value.get(key)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


# HQE_EXPIRY_DAY_NEXT_WEEK_SELECTION_V1
def _next_non_expiring_expiry_timestamp(
    expiry_data: Any,
    trading_date: str,
    *,
    min_dte: int = 1,
) -> str:
    # FYERS uses the nearest expiry when timestamp is blank. On expiry day,
    # that produces DTE=0 rows while HQE requires DTE>=1. Keep normal days
    # unchanged and select the next genuine listed expiry only on DTE=0.
    if not isinstance(expiry_data, list):
        return ""

    try:
        trading_day = date.fromisoformat(str(trading_date))
    except (TypeError, ValueError):
        return ""

    candidates: list[tuple[int, str]] = []
    for row in expiry_data:
        if not isinstance(row, dict):
            continue

        raw_date = (
            row.get("date")
            or row.get("expiry_date")
            or row.get("expiryDate")
        )
        raw_timestamp = (
            row.get("expiry")
            or row.get("expiry_timestamp")
            or row.get("timestamp")
        )
        if raw_date in (None, "") or raw_timestamp in (None, ""):
            continue

        expiry_day = None
        text = str(raw_date).strip()
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                expiry_day = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                continue

        if expiry_day is None:
            continue

        dte = (expiry_day - trading_day).days
        if dte < 0:
            continue
        candidates.append((dte, str(raw_timestamp).strip()))

    candidates.sort(key=lambda item: (item[0], item[1]))
    if not candidates:
        return ""

    # Blank timestamp already chooses the nearest listed expiry. Do not
    # perform a second request on ordinary non-expiry days.
    if candidates[0][0] >= int(min_dte):
        return ""

    for dte, timestamp in candidates:
        if dte >= int(min_dte) and timestamp:
            return timestamp
    return ""


def run_cycle(
    *,
    workspace: Path,
    now: datetime | None = None,
    dependencies: WorkflowDependencies | None = None,
    force: bool = False,
) -> dict[str, Any]:
    current = ist_now(now)
    phase = market_phase(current)
    trading_date = current.date().isoformat()
    deps = dependencies or default_dependencies()

    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)

    if phase == "WEEKEND" and not force:
        return _write_status(
            workspace,
            {
                **_base_payload(
                    workspace=workspace,
                    current=current,
                    status="MARKET_CLOSED_WEEKEND",
                    message=(
                        "Weekend detected. No current-day market report "
                        "will be fabricated."
                    ),
                    stage="SCHEDULE_GUARD",
                ),
                "next_retry_seconds": 1800,
            },
        )

    if phase == "PRE_MARKET" and not force:
        return _write_status(
            workspace,
            {
                **_base_payload(
                    workspace=workspace,
                    current=current,
                    status="WAITING_MARKET_START",
                    message=(
                        "Waiting for the 09:15 IST market window. "
                        "Automatic workflow will start without manual input."
                    ),
                    stage="SCHEDULE_GUARD",
                ),
                "next_retry_seconds": 60,
            },
        )

    existing = status_snapshot(workspace)
    if (
        not force
        and phase == "POST_MARKET"
        and existing.get("status") == "COMPLETE"
        and existing.get("trading_date") == trading_date
    ):
        return existing

    if not _RUN_LOCK.acquire(blocking=False):
        return {
            **status_snapshot(workspace),
            "status": "ALREADY_RUNNING",
            "message": "Automatic daily workflow is already running.",
        }

    try:
        _write_status(
            workspace,
            {
                **_base_payload(
                    workspace=workspace,
                    current=current,
                    status="RUNNING",
                    message=(
                        "Automatic daily data-only workflow is running."
                    ),
                    stage="SECURE_AUTH",
                ),
                "started_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds"),
            },
        )

        try:
            before = deps.auth_status()
            applied = deps.apply_auth(overwrite=True)
            after = deps.auth_status()
        except Exception as exc:
            return _error_status(
                workspace=workspace,
                current=current,
                stage="SECURE_AUTH",
                exc=exc,
            )

        if not bool(after.get("access_token_present")):
            return _write_status(
                workspace,
                {
                    **_base_payload(
                        workspace=workspace,
                        current=current,
                        status="AUTH_REQUIRED",
                        message=(
                            "FYERS secure token is not available. "
                            "Refresh it once from Broker Connect."
                        ),
                        stage="SECURE_AUTH",
                    ),
                    "auth_before": before.get("status", ""),
                    "auth_apply": applied.get("status", ""),
                    "auth_after": after.get("status", ""),
                    "next_retry_seconds": 300,
                },
            )

        try:
            chain_payload = deps.option_chain(
                workspace=workspace,
                symbol=DEFAULT_SYMBOL,
                trading_date=trading_date,
                strike_count=20,
                expiry_timestamp="",
            )
            # HQE_EXPIRY_DAY_NEXT_WEEK_SELECTION_RETRY_V1
            next_expiry_timestamp = (
                _next_non_expiring_expiry_timestamp(
                    chain_payload.get("expiry_data"),
                    trading_date,
                    min_dte=1,
                )
            )
            if next_expiry_timestamp:
                chain_payload = deps.option_chain(
                    workspace=workspace,
                    symbol=DEFAULT_SYMBOL,
                    trading_date=trading_date,
                    strike_count=20,
                    expiry_timestamp=next_expiry_timestamp,
                )
        except Exception as exc:
            return _error_status(
                workspace=workspace,
                current=current,
                stage="OPTION_CHAIN",
                exc=exc,
            )

        readiness = chain_payload.get("readiness")
        if not isinstance(readiness, dict):
            readiness = {}
        if not bool(readiness.get("both_sides_ready")):
            return _write_status(
                workspace,
                {
                    **_base_payload(
                        workspace=workspace,
                        current=current,
                        status="WAITING_MARKET_DATA",
                        message=(
                            "Current-day option chain does not yet contain "
                            "both genuine CE and PE rows."
                        ),
                        stage="OPTION_CHAIN",
                    ),
                    "ce_rows": _safe_count(
                        chain_payload,
                        "readiness",
                        "ce_count",
                    ),
                    "pe_rows": _safe_count(
                        chain_payload,
                        "readiness",
                        "pe_count",
                    ),
                    "next_retry_seconds": 300,
                },
            )

        try:
            history_payload = deps.selected_history(
                workspace=workspace,
                trading_date=trading_date,
            )
        except Exception as exc:
            return _error_status(
                workspace=workspace,
                current=current,
                stage="SELECTED_CE_PE_HISTORY",
                exc=exc,
            )

        if (
            str(history_payload.get("status", "")).strip().upper()
            != "SELECTED_CE_PE_HISTORY_5M_READY"
        ):
            return _write_status(
                workspace,
                {
                    **_base_payload(
                        workspace=workspace,
                        current=current,
                        status="WAITING_MARKET_DATA",
                        message=(
                            "Selected CE and PE historical 5-minute data "
                            "is not both-side ready yet."
                        ),
                        stage="SELECTED_CE_PE_HISTORY",
                    ),
                    "next_retry_seconds": 300,
                },
            )

        try:
            replay_payload = deps.recorded_replay(
                workspace=workspace,
                trading_date=trading_date,
            )
        except Exception as exc:
            return _error_status(
                workspace=workspace,
                current=current,
                stage="RECORDED_REPLAY",
                exc=exc,
            )

        if (
            str(replay_payload.get("status", "")).strip().upper()
            != "RECORDED_DATA_REPLAY_EVALUATED"
        ):
            return _write_status(
                workspace,
                {
                    **_base_payload(
                        workspace=workspace,
                        current=current,
                        status="FAILED_SAFE",
                        message=(
                            "Recorded replay returned an unexpected "
                            "readiness status."
                        ),
                        stage="RECORDED_REPLAY",
                    ),
                    "actual_replay_status": replay_payload.get(
                        "status",
                        "",
                    ),
                    "next_retry_seconds": 300,
                },
            )

        replay_truth = replay_payload.get("replay_truth")
        if not isinstance(replay_truth, dict):
            replay_truth = {}
        safety_ok = all(
            (
                replay_truth.get("paper_trade_created") is False,
                replay_truth.get("position_opened") is False,
                replay_truth.get("pnl_calculated") is False,
                replay_truth.get("historical_execution_claim") is False,
                replay_payload.get("real_orders_allowed") is False,
                replay_payload.get("broker_execution_allowed") is False,
                replay_payload.get("auto_trading_allowed") is False,
                replay_payload.get("option_selling_allowed") is False,
            )
        )
        if not safety_ok:
            return _write_status(
                workspace,
                {
                    **_base_payload(
                        workspace=workspace,
                        current=current,
                        status="SAFETY_BLOCKED",
                        message=(
                            "Replay safety truth is incomplete. "
                            "Today Report publication is blocked."
                        ),
                        stage="SAFETY_VERIFY",
                    ),
                    "next_retry_seconds": 900,
                },
            )

        outputs = replay_payload.get("outputs")
        if not isinstance(outputs, dict):
            outputs = {}

        result = {
            **_base_payload(
                workspace=workspace,
                current=current,
                status="COMPLETE",
                message=(
                    "Current-day genuine FYERS option data, selected "
                    "CE/PE history and truthful SMC replay report are ready."
                ),
                stage="COMPLETE",
            ),
            "auth_before": before.get("status", ""),
            "auth_apply": applied.get("status", ""),
            "auth_after": after.get("status", ""),
            "option_chain": {
                "ce_rows": _safe_count(
                    chain_payload,
                    "readiness",
                    "ce_count",
                ),
                "pe_rows": _safe_count(
                    chain_payload,
                    "readiness",
                    "pe_count",
                ),
                "both_sides_ready": True,
            },
            "selected_history": {
                "ce_rows": _safe_count(
                    history_payload,
                    "rows",
                    "ce",
                ),
                "pe_rows": _safe_count(
                    history_payload,
                    "rows",
                    "pe",
                ),
                "combined_rows": _safe_count(
                    history_payload,
                    "rows",
                    "combined",
                ),
                "selection": history_payload.get("selection", {}),
            },
            "recorded_replay": {
                "index_rows": _safe_count(
                    replay_payload,
                    "index_rows",
                ),
                "evaluation_count": _safe_count(
                    replay_payload,
                    "evaluation_count",
                ),
                "accepted_evaluation_count": _safe_count(
                    replay_payload,
                    "accepted_evaluation_count",
                ),
                "decision_counts": replay_payload.get(
                    "decision_counts",
                    {},
                ),
                "accepted_side_counts": replay_payload.get(
                    "accepted_side_counts",
                    {},
                ),
                "signal_generated": bool(
                    replay_payload.get("signal_generated")
                ),
            },
            "outputs": outputs,
            "next_retry_seconds": (
                DEFAULT_INTERVAL_SECONDS
                if phase == "MARKET_ACTIVE"
                else 1800
            ),
        }
        return _write_status(workspace, result)
    finally:
        _RUN_LOCK.release()


def _sleep_seconds(payload: dict[str, Any]) -> int:
    try:
        value = int(payload.get("next_retry_seconds") or 0)
    except (TypeError, ValueError):
        value = 0
    return min(1800, max(30, value or DEFAULT_INTERVAL_SECONDS))


def background_loop(
    workspace: Path,
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> None:
    while True:
        try:
            payload = run_cycle(workspace=workspace)
            sleep_for = _sleep_seconds(payload)
            if payload.get("status") in {
                "COMPLETE",
                "WAITING_MORE_DATA",
                "WAITING_MARKET_DATA",
            } and market_phase() == "MARKET_ACTIVE":
                sleep_for = max(30, interval_seconds)
        except Exception as exc:
            current = ist_now()
            _error_status(
                workspace=workspace,
                current=current,
                stage="BACKGROUND_LOOP",
                exc=exc,
            )
            sleep_for = max(60, interval_seconds)
        time_module.sleep(sleep_for)


def launch_app_background_worker(
    workspace: Path,
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> dict[str, Any]:
    if (
        os.environ.get("PYTEST_CURRENT_TEST")
        or "pytest" in sys.modules
        or os.environ.get(
            "HQE_DISABLE_AUTOMATIC_DAILY_WORKFLOW",
            "",
        ).strip()
        in {"1", "true", "TRUE", "yes", "YES"}
    ):
        return {
            "started": False,
            "status": "DISABLED_FOR_TEST_OR_OPERATOR",
        }

    key = str(workspace.resolve()).lower()
    existing = _WORKERS.get(key)
    if existing is not None and existing.is_alive():
        return {
            "started": False,
            "status": "ALREADY_RUNNING",
            "thread_name": existing.name,
        }

    worker = threading.Thread(
        target=background_loop,
        kwargs={
            "workspace": workspace,
            "interval_seconds": interval_seconds,
        },
        name="HQEAutomaticDailyCurrentDayWorkflow",
        daemon=True,
    )
    _WORKERS[key] = worker
    worker.start()
    return {
        "started": True,
        "status": "RUNNING_BACKGROUND",
        "thread_name": worker.name,
        "paper_only": True,
        "data_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "guard_check_status": "PASS",
        "automatic_daily_workflow": True,
        "app_background_worker": True,
        "live_api_call_performed": False,
        "paper_trade_created": False,
        "position_opened": False,
        "pnl_calculated": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "safety_lock": AUTOMATIC_SAFETY,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Automatically build the current-day genuine FYERS "
            "option-data and truthful recorded replay report."
        )
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
    )
    parser.add_argument("--guard-check", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0

    if args.workspace is None:
        raise SystemExit("--workspace is required.")

    if args.run_once:
        payload = run_cycle(
            workspace=args.workspace,
            force=args.force,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("status") in {
            "COMPLETE",
            "WAITING_MARKET_START",
            "WAITING_MORE_DATA",
            "WAITING_MARKET_DATA",
            "MARKET_CLOSED_WEEKEND",
            "MARKET_CLOSED_OR_HOLIDAY",
            "AUTH_REQUIRED",
        } else 2

    if args.watch:
        background_loop(
            args.workspace,
            interval_seconds=max(30, args.interval_seconds),
        )
        return 0

    raise SystemExit(
        "Use --guard-check, --run-once or --watch."
    )


if __name__ == "__main__":
    raise SystemExit(main())
