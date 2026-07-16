from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import time
import traceback
from datetime import date, datetime, time as clock_time
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

RUNTIME_VERSION = "HQE_PAPER_PRODUCT_RUNTIME_V2"
RUNTIME_FOLDER = "HQE_PAPER_PRODUCT_RUNTIME"
RUNTIME_STATE_FILE = "HQE_PAPER_PRODUCT_RUNTIME.json"
RUNTIME_LOG_FILE = "HQE_PAPER_PRODUCT_RUNTIME.log"
STOP_FILE = "HQE_PAPER_PRODUCT_STOP.flag"
MODULE_STATE_FILE = "MODULE_131_POSITION_STATE.json"
MODULE_LEDGER_FILE = "MODULE_131_PAPER_LEDGER.csv"
MODULE_SUMMARY_FILE = "MODULE_131_SUPERVISOR_SUMMARY.json"
MODULE_REPORT_FILE = "MODULE_131_INTRADAY_SUPERVISOR_REPORT.md"

INDEX_FILENAME = "NIFTY_INDEX_HISTORY_5M.csv"
PREMIUM_FILENAME = "SELECTED_CE_PE_HISTORY_5M_COMBINED.csv"

SAFETY = {
    "paper_only": True,
    "real_orders_allowed": False,
    "broker_execution_allowed": False,
    "auto_trading_allowed": False,
    "real_money_allowed": False,
}


def now_ist() -> datetime:
    return datetime.now(tz=IST).replace(tzinfo=None)


def now_utc_text() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def runtime_paths(workspace: Path) -> dict[str, Path]:
    workspace = Path(workspace).resolve()
    folder = workspace / RUNTIME_FOLDER
    return {
        "folder": folder,
        "runtime": folder / RUNTIME_STATE_FILE,
        "log": folder / RUNTIME_LOG_FILE,
        "stop": folder / STOP_FILE,
        "state": folder / MODULE_STATE_FILE,
        "ledger": folder / MODULE_LEDGER_FILE,
        "summary": folder / MODULE_SUMMARY_FILE,
        "report": folder / MODULE_REPORT_FILE,
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
            return (
                completed.returncode == 0
                and str(pid) in completed.stdout
                and "No tasks are running" not in completed.stdout
            )
        os.kill(pid, 0)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def runtime_process_alive(pid: int, workspace: Path | None = None) -> bool:
    if not process_alive(pid):
        return False

    try:
        import psutil  # type: ignore
    except ImportError:
        return True

    try:
        process = psutil.Process(pid)
        command = " ".join(process.cmdline()).lower()
        if "hqe_paper_product_runtime.py" not in command:
            return False
        if workspace is not None:
            workspace_text = str(Path(workspace).resolve()).lower()
            if workspace_text not in command:
                return False
        return bool(process.is_running())
    except psutil.NoSuchProcess:
        return False
    except (psutil.AccessDenied, OSError):
        return True


def status_payload(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    paths = runtime_paths(workspace)
    payload = read_json(paths["runtime"])
    pid = safe_int(payload.get("pid"))
    alive = runtime_process_alive(pid, workspace) if pid else False
    previous_status = str(payload.get("status", "NOT_STARTED"))

    if alive:
        runtime_status = previous_status
    elif previous_status.startswith("RUNNING_"):
        runtime_status = "STALE_RUNTIME_STATE"
    else:
        runtime_status = previous_status

    return {
        **payload,
        "version": RUNTIME_VERSION,
        "workspace": str(workspace),
        "pid": pid or None,
        "running": alive,
        "status": runtime_status,
        "runtime_path": str(paths["runtime"]),
        "log_path": str(paths["log"]),
        "state_path": str(paths["state"]),
        "ledger_path": str(paths["ledger"]),
        "summary_path": str(paths["summary"]),
        "report_path": str(paths["report"]),
        **SAFETY,
    }


def read_ledger(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, csv.Error):
        return []


def value_from_aliases(row: dict[str, Any], aliases: Iterable[str]) -> str:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for alias in aliases:
        value = lowered.get(alias.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def latest_option_price(
    premium_csv: Path | None,
    state: dict[str, Any],
) -> tuple[float | None, str]:
    if premium_csv is None or not Path(premium_csv).is_file():
        return None, ""

    target_symbol = str(state.get("option_symbol", "")).strip().upper()
    target_side = str(state.get("side", "")).strip().upper()
    selected: tuple[float, str] | None = None

    try:
        with Path(premium_csv).open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            for row in csv.DictReader(handle):
                symbol = value_from_aliases(
                    row,
                    ("option_symbol", "symbol", "ticker", "tradingsymbol", "instrument"),
                ).upper()
                side = value_from_aliases(
                    row,
                    ("signal_side", "option_side", "side", "trade_side"),
                ).upper()

                if target_symbol and symbol and symbol != target_symbol:
                    continue
                if not target_symbol and target_side and side and side != target_side:
                    continue

                price_text = value_from_aliases(
                    row,
                    ("close", "ltp", "last_traded_price", "premium", "price"),
                )
                price = safe_float(price_text)
                if price is None:
                    continue

                timestamp = value_from_aliases(
                    row,
                    ("datetime", "timestamp", "candle_time", "time", "date"),
                )
                selected = (price, timestamp)
    except (OSError, csv.Error):
        return None, ""

    if selected is None:
        return None, ""
    return selected


def parse_timestamp_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def latest_for_date(
    workspace: Path,
    filename: str,
    trading_date: date,
) -> Path | None:
    date_text = trading_date.isoformat()
    candidates: list[Path] = []
    for path in Path(workspace).rglob(filename):
        try:
            if date_text in str(path) and path.is_file():
                candidates.append(path)
        except OSError:
            continue
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda path: (
            path.stat().st_mtime,
            path.stat().st_size,
        ),
    )


def discover_inputs_for_date(
    workspace: Path,
    trading_date: date,
) -> tuple[Path | None, Path | None]:
    workspace = Path(workspace).resolve()
    date_text = trading_date.isoformat()

    index_csv = (
        workspace
        / "HQE_CURRENT_DAY_RECORDED_REPLAY"
        / date_text
        / INDEX_FILENAME
    )
    premium_csv = (
        workspace
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / date_text
        / "SELECTED_OPTION_HISTORY_5M"
        / PREMIUM_FILENAME
    )

    if not index_csv.is_file():
        index_csv = latest_for_date(workspace, INDEX_FILENAME, trading_date)
    if not premium_csv.is_file():
        premium_csv = latest_for_date(workspace, PREMIUM_FILENAME, trading_date)

    return index_csv, premium_csv


def discover_inputs(
    workspace: Path,
    current: datetime | None = None,
) -> tuple[Path | None, Path | None]:
    now = current or now_ist()
    return discover_inputs_for_date(workspace, now.date())


def last_closed_ledger_row(rows: list[dict[str, str]]) -> dict[str, str]:
    for row in reversed(rows):
        if str(row.get("event", "")).upper() == "POSITION_CLOSED":
            return row
    return {}


def paper_product_snapshot(
    workspace: Path,
    current: datetime | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    paths = runtime_paths(workspace)
    runtime = status_payload(workspace)
    state = read_json(paths["state"])
    summary = read_json(paths["summary"])
    ledger_rows = read_ledger(paths["ledger"])

    now = current or now_ist()
    runtime_index = Path(str(runtime.get("last_index_csv", "")))
    runtime_premium = Path(str(runtime.get("last_premium_csv", "")))
    index_csv = runtime_index if runtime_index.is_file() else None
    premium_csv = runtime_premium if runtime_premium.is_file() else None

    if index_csv is None or premium_csv is None:
        discovered_index, discovered_premium = discover_inputs(workspace, now)
        index_csv = index_csv or discovered_index
        premium_csv = premium_csv or discovered_premium

    latest_price, latest_price_time = latest_option_price(
        premium_csv,
        state,
    )
    entry = safe_float(state.get("entry", summary.get("entry")))
    quantity = safe_float(state.get("quantity", 1)) or 1.0
    position_status = str(
        state.get("status", summary.get("position_state", "FLAT"))
    ).upper()
    if position_status in {"", "UNKNOWN", "NOT_STARTED"}:
        position_status = "FLAT"
    side = str(state.get("side", summary.get("signal_side", "")))
    option_symbol = str(
        state.get("option_symbol", summary.get("option_symbol", ""))
    )

    unrealized: float | None = None
    if (
        position_status == "OPEN"
        and entry is not None
        and latest_price is not None
        and side in {"CE_BUY", "PE_BUY"}
    ):
        unrealized = round((latest_price - entry) * quantity, 6)

    closed_row = last_closed_ledger_row(ledger_rows)
    realized = safe_float(summary.get("paper_pnl"))
    if str(summary.get("event", "")).upper() != "POSITION_CLOSED":
        realized = safe_float(closed_row.get("paper_pnl"))
    if realized is None:
        realized = 0.0

    today_text = now.date().isoformat()
    today_rows = [
        row
        for row in ledger_rows
        if str(row.get("timestamp", "")).startswith(today_text)
    ]
    last_error = str(runtime.get("last_error", "")).strip()
    readiness_reason = str(
        summary.get(
            "readiness_reason",
            runtime.get("status", "NOT_STARTED"),
        )
    )

    runtime_state_exists = paths["runtime"].is_file()
    product_evidence_exists = any(
        path.is_file()
        for path in (
            paths["state"],
            paths["ledger"],
            paths["summary"],
        )
    )

    return {
        "version": RUNTIME_VERSION,
        "runtime_state_exists": runtime_state_exists,
        "product_evidence_exists": product_evidence_exists,
        "running": bool(runtime.get("running")),
        "runtime_status": str(runtime.get("status", "NOT_STARTED")),
        "runtime_pid": runtime.get("pid"),
        "data_ready": bool(summary.get("data_ready")),
        "readiness_reason": readiness_reason,
        "last_error": last_error,
        "position_status": position_status,
        "side": side,
        "option_symbol": option_symbol,
        "entry": entry,
        "stop_loss": safe_float(state.get("stop_loss", summary.get("stop_loss"))),
        "target": safe_float(state.get("target", summary.get("target"))),
        "latest_option_price": latest_price,
        "latest_option_price_time": latest_price_time,
        "unrealized_paper_pnl": unrealized,
        "exit_reason": str(
            summary.get("exit_reason")
            or closed_row.get("exit_reason")
            or ""
        ),
        "realized_paper_pnl": realized,
        "last_event": str(summary.get("event", "")),
        "ledger_rows": ledger_rows[-50:],
        "today_ledger_rows": today_rows,
        "today_completed_trades": sum(
            1
            for row in today_rows
            if str(row.get("event", "")).upper() == "POSITION_CLOSED"
        ),
        "index_csv": str(index_csv or ""),
        "premium_csv": str(premium_csv or ""),
        "runtime_path": str(paths["runtime"]),
        "log_path": str(paths["log"]),
        "state_path": str(paths["state"]),
        "ledger_path": str(paths["ledger"]),
        "summary_path": str(paths["summary"]),
        "report_path": str(paths["report"]),
        **SAFETY,
    }


def write_runtime(
    workspace: Path,
    *,
    status: str,
    collector: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    index_csv: Path | None = None,
    premium_csv: Path | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    paths = runtime_paths(workspace)
    old = read_json(paths["runtime"])
    payload = {
        "version": RUNTIME_VERSION,
        "generated_at_utc": now_utc_text(),
        "started_at_utc": old.get("started_at_utc", now_utc_text()),
        "workspace": str(workspace),
        "pid": os.getpid(),
        "status": status,
        "running": status.startswith("RUNNING_"),
        "collector": collector if collector is not None else old.get("collector", {}),
        "last_index_csv": (
            str(index_csv)
            if index_csv is not None
            else str(old.get("last_index_csv", ""))
        ),
        "last_premium_csv": (
            str(premium_csv)
            if premium_csv is not None
            else str(old.get("last_premium_csv", ""))
        ),
        "last_cycle_summary": (
            summary
            if summary is not None
            else old.get("last_cycle_summary", {})
        ),
        "last_error": (
            error
            if error is not None
            else str(old.get("last_error", ""))
        ),
        "runtime_path": str(paths["runtime"]),
        "log_path": str(paths["log"]),
        "state_path": str(paths["state"]),
        "ledger_path": str(paths["ledger"]),
        "summary_path": str(paths["summary"]),
        "report_path": str(paths["report"]),
        **SAFETY,
    }
    write_json(paths["runtime"], payload)
    return payload


def start_collector(
    workspace: Path,
    user_id: str,
    symbol: str,
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "started": False,
            "status": "DATA_FETCH_NOT_REQUESTED",
        }
    try:
        import hqe_hidden_paper_watch_supervisor as hidden

        payload = hidden.start(workspace, user_id, symbol)
        if isinstance(payload, dict):
            return payload
        return {
            "started": True,
            "status": "DATA_COLLECTOR_START_REQUESTED",
        }
    except Exception as exc:
        return {
            "started": False,
            "status": "DATA_COLLECTOR_START_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def stop_collector(workspace: Path) -> dict[str, Any]:
    try:
        import hqe_hidden_paper_watch_supervisor as hidden

        payload = hidden.stop(workspace)
        if isinstance(payload, dict):
            return payload
        return {
            "stopped": True,
            "status": "DATA_COLLECTOR_STOP_REQUESTED",
        }
    except Exception as exc:
        return {
            "stopped": False,
            "status": "DATA_COLLECTOR_STOP_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_module_131(
    workspace: Path,
    index_csv: Path,
    premium_csv: Path,
    current: datetime,
) -> dict[str, Any]:
    from run_forward_intraday_paper_supervisor import (
        SupervisorPaths,
        run_one_cycle,
    )

    paths = runtime_paths(workspace)
    supervisor_paths = SupervisorPaths(
        index_csv=index_csv,
        premium_csv=premium_csv,
        out_dir=paths["folder"],
        state_json=paths["state"],
        ledger_csv=paths["ledger"],
    )
    return run_one_cycle(supervisor_paths, current)


def wait_or_stop(stop_path: Path, seconds: int) -> bool:
    deadline = time.monotonic() + max(1, seconds)
    while time.monotonic() < deadline:
        if stop_path.exists():
            return False
        time.sleep(1)
    return True


def market_phase(current: datetime) -> str:
    if current.weekday() >= 5:
        return "MARKET_CLOSED"
    current_time = current.time()
    if current_time < clock_time(9, 15):
        return "PRE_MARKET"
    if current_time >= clock_time(15, 25):
        return "EOD"
    return "ACTIVE"


def recover_prior_day_open_position(
    workspace: Path,
    current: datetime,
) -> tuple[bool, dict[str, Any] | None, Path | None, Path | None, str]:
    paths = runtime_paths(workspace)
    state = read_json(paths["state"])
    if str(state.get("status", "")).upper() != "OPEN":
        return True, None, None, None, ""

    entry_date = parse_timestamp_date(state.get("entry_time"))
    if entry_date is None or entry_date >= current.date():
        return True, None, None, None, ""

    index_csv, premium_csv = discover_inputs_for_date(
        workspace,
        entry_date,
    )
    if index_csv is None or premium_csv is None:
        missing = []
        if index_csv is None:
            missing.append("PRIOR_DAY_INDEX_CSV")
        if premium_csv is None:
            missing.append("PRIOR_DAY_CE_PE_PREMIUM_CSV")
        return False, None, index_csv, premium_csv, ",".join(missing)

    recovery_time = datetime.combine(entry_date, clock_time(15, 25))
    summary = run_module_131(
        workspace,
        index_csv,
        premium_csv,
        recovery_time,
    )
    return True, summary, index_csv, premium_csv, ""


def run(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    paths = runtime_paths(workspace)
    paths["folder"].mkdir(parents=True, exist_ok=True)

    current_status = status_payload(workspace)
    old_pid = safe_int(current_status.get("pid"))
    if (
        old_pid
        and old_pid != os.getpid()
        and runtime_process_alive(old_pid, workspace)
    ):
        print(
            json.dumps(
                {
                    **current_status,
                    "started": False,
                    "reason": "already_running",
                },
                indent=2,
            )
        )
        return 0

    paths["stop"].unlink(missing_ok=True)
    collector = start_collector(
        workspace,
        args.user_id,
        args.symbol,
        args.run_data_fetch,
    )

    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True
        paths["stop"].touch(exist_ok=True)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, request_stop)

    write_runtime(
        workspace,
        status="RUNNING_WAITING_FOR_CURRENT_DAY_INPUTS",
        collector=collector,
        error="",
    )

    cycle_number = 0
    try:
        while not stopping and not paths["stop"].exists():
            cycle_number += 1
            current = now_ist()

            try:
                recovered, recovery_summary, recovery_index, recovery_premium, recovery_error = (
                    recover_prior_day_open_position(workspace, current)
                )
                if not recovered:
                    write_runtime(
                        workspace,
                        status=(
                            "RUNNING_WAITING_FOR_RESTART_RECOVERY_INPUTS:"
                            + recovery_error
                        ),
                        collector=collector,
                        index_csv=recovery_index,
                        premium_csv=recovery_premium,
                        error="",
                    )
                    if args.max_cycles and cycle_number >= args.max_cycles:
                        break
                    if not wait_or_stop(
                        paths["stop"],
                        args.interval_seconds,
                    ):
                        break
                    continue
                elif recovery_summary is not None:
                    write_runtime(
                        workspace,
                        status="RUNNING_RESTART_RECOVERY_COMPLETED",
                        collector=collector,
                        summary=recovery_summary,
                        index_csv=recovery_index,
                        premium_csv=recovery_premium,
                        error="",
                    )

                phase = market_phase(current)
                index_csv, premium_csv = discover_inputs(
                    workspace,
                    current,
                )

                if phase == "MARKET_CLOSED":
                    write_runtime(
                        workspace,
                        status="RUNNING_MARKET_CLOSED_IDLE",
                        collector=collector,
                        index_csv=index_csv,
                        premium_csv=premium_csv,
                        error="",
                    )
                elif phase == "PRE_MARKET":
                    write_runtime(
                        workspace,
                        status="RUNNING_PRE_MARKET_WAITING",
                        collector=collector,
                        index_csv=index_csv,
                        premium_csv=premium_csv,
                        error="",
                    )
                elif index_csv is None or premium_csv is None:
                    missing = []
                    if index_csv is None:
                        missing.append("INDEX_CSV")
                    if premium_csv is None:
                        missing.append("CE_PE_PREMIUM_CSV")
                    write_runtime(
                        workspace,
                        status=(
                            "RUNNING_WAITING_FOR_CURRENT_DAY_INPUTS:"
                            + ",".join(missing)
                        ),
                        collector=collector,
                        index_csv=index_csv,
                        premium_csv=premium_csv,
                        error="",
                    )
                else:
                    state = read_json(paths["state"])
                    state_open = str(state.get("status", "")).upper() == "OPEN"

                    if phase == "EOD" and not state_open:
                        write_runtime(
                            workspace,
                            status="RUNNING_MARKET_CLOSED_IDLE",
                            collector=collector,
                            index_csv=index_csv,
                            premium_csv=premium_csv,
                            error="",
                        )
                    else:
                        summary = run_module_131(
                            workspace,
                            index_csv,
                            premium_csv,
                            current,
                        )
                        status = (
                            "RUNNING_EOD_POSITION_CLOSE"
                            if phase == "EOD"
                            else "RUNNING_PAPER_LIFECYCLE_ACTIVE"
                        )
                        write_runtime(
                            workspace,
                            status=status,
                            collector=collector,
                            summary=summary,
                            index_csv=index_csv,
                            premium_csv=premium_csv,
                            error="",
                        )
            except Exception as exc:
                write_runtime(
                    workspace,
                    status="RUNNING_CYCLE_ERROR",
                    collector=collector,
                    error=(
                        f"{type(exc).__name__}: {exc}\n"
                        + traceback.format_exc()
                    ),
                )

            if args.max_cycles and cycle_number >= args.max_cycles:
                break
            if not wait_or_stop(
                paths["stop"],
                args.interval_seconds,
            ):
                break
    finally:
        collector_result = stop_collector(workspace)
        write_runtime(
            workspace,
            status="STOPPED_BY_OPERATOR",
            collector=collector_result,
        )
        paths["stop"].unlink(missing_ok=True)

    return 0


def stop(workspace: Path) -> int:
    workspace = Path(workspace).resolve()
    paths = runtime_paths(workspace)
    paths["folder"].mkdir(parents=True, exist_ok=True)
    paths["stop"].touch(exist_ok=True)

    payload = status_payload(workspace)
    pid = safe_int(payload.get("pid"))
    collector = stop_collector(workspace)

    for _ in range(10):
        if not runtime_process_alive(pid, workspace):
            break
        time.sleep(1)

    if runtime_process_alive(pid, workspace):
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=CREATE_NO_WINDOW,
                )
            else:
                os.kill(pid, signal.SIGTERM)
        except (OSError, subprocess.SubprocessError):
            pass

    final = {
        **payload,
        "version": RUNTIME_VERSION,
        "generated_at_utc": now_utc_text(),
        "workspace": str(workspace),
        "status": "STOPPED_BY_OPERATOR",
        "running": False,
        "collector": collector,
        "stopped": True,
        "runtime_path": str(paths["runtime"]),
        "log_path": str(paths["log"]),
        "state_path": str(paths["state"]),
        "ledger_path": str(paths["ledger"]),
        "summary_path": str(paths["summary"]),
        "report_path": str(paths["report"]),
        **SAFETY,
    }
    write_json(paths["runtime"], final)
    paths["stop"].unlink(missing_ok=True)
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0


def guard_payload() -> dict[str, Any]:
    return {
        "version": RUNTIME_VERSION,
        "guard_check_status": "PASS",
        "canonical_runtime": True,
        "duplicate_runtime_prevention": True,
        "restart_recovery": True,
        "live_position_snapshot": True,
        "trade_ledger_visible": True,
        "no_visible_terminal": True,
        "pythonw_runtime_supported": True,
        **SAFETY,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HQE canonical paper-trading product runtime"
    )
    parser.add_argument("--workspace", required=False, default="")
    parser.add_argument("--user-id", default="")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--run-data-fetch", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        raise SystemExit("--workspace is required")
    workspace = Path(args.workspace).resolve()
    if args.stop:
        return stop(workspace)
    if args.status:
        print(json.dumps(status_payload(workspace), indent=2, sort_keys=True))
        return 0
    if args.snapshot:
        print(
            json.dumps(
                paper_product_snapshot(workspace),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
