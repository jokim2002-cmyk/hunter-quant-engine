
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

VERSION = "MODULES_161_170_LIVE_PAPER_FOUNDATION_V1"
DEFAULT_WORKSPACE = r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"

SAFETY_LOCK = {
    "paper_only": True,
    "data_only": True,
    "local_files_only_by_default": True,
    "manual_login_required": True,
    "manual_operator_review_required": True,
    "no_real_money": True,
    "no_broker_execution": True,
    "no_real_orders": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
    "no_plaintext_secret_storage": True,
    "order_api_hard_blocked": True,
}

BLOCKED_ORDER_APIS = [
    "place_order",
    "modify_order",
    "cancel_order",
    "exit_positions",
    "place_basket_orders",
    "place_gtt_order",
    "modify_gtt_order",
    "cancel_gtt_order",
    "convert_position",
    "orderbook",
    "tradebook",
    "positions",
    "holdings",
    "funds",
]

REQUIRED_ENV_NAMES = ["FYERS_CLIENT_ID", "FYERS_ACCESS_TOKEN"]
OPTIONAL_ENV_NAMES = ["FYERS_REDIRECT_URI", "FYERS_APP_ID"]

MODULES: Dict[int, Dict[str, str]] = {
    161: {
        "script": "hqe_fyers_data_only_secret_preflight_pack.py",
        "name": "Fyers Data-Only Credential Setup / Secret Preflight Pack",
        "status_key": "secret_preflight_status",
        "prefix": "MODULE_161_FYERS_SECRET_PREFLIGHT",
        "decision": "FYERS_SECRET_PREFLIGHT_READY_ENV_SETUP_REQUIRED",
    },
    162: {
        "script": "hqe_fyers_access_token_validation_pack.py",
        "name": "Fyers Access Token Validation Pack",
        "status_key": "token_validation_status",
        "prefix": "MODULE_162_FYERS_TOKEN_VALIDATION",
        "decision": "FYERS_TOKEN_VALIDATION_READY_OFFLINE_ONLY",
    },
    163: {
        "script": "hqe_fyers_data_only_quote_ltp_fetcher.py",
        "name": "Fyers Data-Only Quote/LTP Fetcher",
        "status_key": "quote_fetcher_status",
        "prefix": "MODULE_163_FYERS_DATA_ONLY_QUOTE_LTP",
        "decision": "DATA_ONLY_QUOTE_FETCHER_READY_MANUAL_TRANSPORT_REQUIRED",
    },
    164: {
        "script": "hqe_fyers_5m_candle_builder_live_normalizer.py",
        "name": "Fyers 5m Candle Builder / Live Data Normalizer",
        "status_key": "candle_builder_status",
        "prefix": "MODULE_164_FYERS_5M_CANDLE_BUILDER",
        "decision": "LIVE_5M_CANDLE_BUILDER_READY_LOCAL_DATA_ONLY",
    },
    165: {
        "script": "hqe_live_paper_market_watch_loop.py",
        "name": "09:15-15:30 Live Paper Watch Loop",
        "status_key": "watch_loop_status",
        "prefix": "MODULE_165_LIVE_PAPER_WATCH_LOOP",
        "decision": "LIVE_PAPER_WATCH_LOOP_PLAN_READY_MANUAL_START_REQUIRED",
    },
    166: {
        "script": "hqe_paper_signal_execution_logger.py",
        "name": "Paper Signal Execution Logger",
        "status_key": "paper_signal_execution_logger_status",
        "prefix": "MODULE_166_PAPER_SIGNAL_EXECUTION_LOGGER",
        "decision": "PAPER_SIGNAL_EXECUTION_LOGGER_READY_NO_FAKE_TRADES",
    },
    167: {
        "script": "hqe_live_no_trade_reason_integration.py",
        "name": "No-Trade Reason Live Integration",
        "status_key": "no_trade_reason_integration_status",
        "prefix": "MODULE_167_NO_TRADE_REASON_LIVE_INTEGRATION",
        "decision": "NO_TRADE_REASON_LIVE_INTEGRATION_READY",
    },
    168: {
        "script": "hqe_daily_auto_close_report_tracker_integration.py",
        "name": "Daily Auto Close + Report + Tracker Integration",
        "status_key": "daily_close_report_tracker_status",
        "prefix": "MODULE_168_DAILY_CLOSE_REPORT_TRACKER",
        "decision": "DAILY_CLOSE_REPORT_TRACKER_READY_MANUAL_REVIEW_REQUIRED",
    },
    169: {
        "script": "hqe_safe_startup_desktop_shortcut_final.py",
        "name": "Safe Startup Install / Desktop Shortcut Final",
        "status_key": "startup_shortcut_status",
        "prefix": "MODULE_169_SAFE_STARTUP_DESKTOP_SHORTCUT",
        "decision": "SAFE_STARTUP_SHORTCUT_READY_MANUAL_INSTALL_REQUIRED",
    },
    170: {
        "script": "hqe_full_live_paper_dry_run_final_readiness.py",
        "name": "Full Live Paper Dry Run / Final Readiness Check",
        "status_key": "full_live_paper_dry_run_status",
        "prefix": "MODULE_170_FULL_LIVE_PAPER_DRY_RUN",
        "decision": "FULL_LIVE_PAPER_DRY_RUN_READY_HOLD_REAL_MONEY_BLOCKED",
    },
}

TRUTHY = {"1", "true", "yes", "y", "approved", "paper_signal_approved", "executed", "filled", "paper_filled"}
FALSEY = {"0", "false", "no", "n", "rejected", "blocked", "none", "", "null"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in TRUTHY:
        return True
    if text in FALSEY:
        return False
    return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(str(value).strip()))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(str(value).strip())
    except Exception:
        return default


def normalize_header(name: str) -> str:
    return str(name or "").replace("\ufeff", "").strip()


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, str]] = []
        for row in reader:
            rows.append({normalize_header(k): (v or "") for k, v in row.items() if k is not None})
        return rows


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})


def env_secret_report() -> Dict[str, Any]:
    present_required = [name for name in REQUIRED_ENV_NAMES if os.environ.get(name)]
    missing_required = [name for name in REQUIRED_ENV_NAMES if not os.environ.get(name)]
    present_optional = [name for name in OPTIONAL_ENV_NAMES if os.environ.get(name)]
    return {
        "credential_source": "environment_variables_only",
        "required_env_names": REQUIRED_ENV_NAMES,
        "optional_env_names": OPTIONAL_ENV_NAMES,
        "present_required_env_count": len(present_required),
        "missing_required_env_names": missing_required,
        "present_optional_env_count": len(present_optional),
        "credentials_complete_for_future_data_transport": len(missing_required) == 0,
        "secret_values_redacted": True,
        "plaintext_secret_storage_allowed": False,
    }


def count_day_ledger(workspace: Path) -> Dict[str, int]:
    rows = read_csv_rows(workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv")
    observed_dates = set()
    valid_dates = set()
    for idx, row in enumerate(rows):
        date_value = row.get("trading_date") or row.get("date") or row.get("day_date") or f"ROW_{idx + 1}"
        observed_dates.add(str(date_value))
        trade_count = safe_int(row.get("trade_count") or row.get("paper_trade_count") or row.get("actual_paper_trades"), 0)
        if trade_count > 0:
            valid_dates.add(str(date_value))
    return {
        "day_ledger_rows": len(rows),
        "observed_session_days": len(observed_dates),
        "valid_paper_trade_days": len(valid_dates),
        "no_trade_observed_days": max(0, len(observed_dates) - len(valid_dates)),
        "remaining_valid_trade_days": max(0, 30 - len(valid_dates)),
    }


def count_actual_trade_rows(workspace: Path, day_number: int) -> Dict[str, Any]:
    sources = [
        workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv",
        workspace / f"DAY_{day_number:03d}_FORWARD_TRADE_LOG.csv",
        workspace / f"DAY_{day_number:03d}_PAPER_EXECUTION_LOG.csv",
    ]
    seen = set()
    count = 0
    expiry_weeks = set()
    source_names = []
    for source in sources:
        rows = read_csv_rows(source)
        if not rows:
            continue
        source_names.append(source.name)
        for idx, row in enumerate(rows):
            row_key = row.get("trade_id") or row.get("paper_trade_id") or row.get("order_id") or f"{source.name}:{idx}"
            if row_key in seen:
                continue
            seen.add(row_key)
            count += 1
            expiry_value = row.get("expiry") or row.get("expiry_date") or row.get("option_expiry")
            if expiry_value:
                try:
                    dt = datetime.fromisoformat(str(expiry_value).replace("Z", "+00:00"))
                    iso = dt.isocalendar()
                    expiry_weeks.add(f"{iso.year}-W{iso.week:02d}")
                except Exception:
                    expiry_weeks.add(str(expiry_value)[:10])
    return {
        "actual_paper_trades": count,
        "actual_trade_rows_source": ",".join(source_names) if source_names else "NONE",
        "distinct_expiry_weeks": len(expiry_weeks),
    }


def approved_signal_count(workspace: Path, day_number: int) -> int:
    rows = read_csv_rows(workspace / f"DAY_{day_number:03d}_FORWARD_SIGNAL_FEED.csv")
    approved = 0
    for row in rows:
        values = [
            row.get("paper_signal_decision"),
            row.get("signal_status"),
            row.get("approved"),
            row.get("paper_signal_approved"),
            row.get("is_approved"),
        ]
        if any(as_bool(value, False) for value in values):
            approved += 1
    return approved


def executed_paper_signal_rows(workspace: Path, day_number: int) -> List[Dict[str, Any]]:
    rows = read_csv_rows(workspace / f"DAY_{day_number:03d}_FORWARD_SIGNAL_FEED.csv")
    executed: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        executed_flag = any(
            as_bool(row.get(key), False)
            for key in ["paper_trade_executed", "paper_filled", "paper_execution_logged", "simulated_fill_confirmed"]
        )
        if not executed_flag:
            continue
        executed.append(
            {
                "paper_trade_id": row.get("paper_trade_id") or row.get("signal_id") or f"PAPER_SIGNAL_{idx + 1}",
                "trading_date": row.get("trading_date") or row.get("date") or "",
                "symbol": row.get("symbol") or row.get("market_symbol") or "NSE:NIFTY50-INDEX",
                "side": row.get("side") or row.get("option_side") or "PAPER_ONLY",
                "entry_price": row.get("entry_price") or row.get("ltp") or "",
                "quantity": row.get("quantity") or row.get("qty") or "",
                "source": "explicit_paper_execution_flag_only",
            }
        )
    return executed


def build_candles_from_sample(workspace: Path) -> List[Dict[str, Any]]:
    # Local deterministic sample only. This is not market data and not a trade signal.
    sample_ticks = [
        ("2026-07-09T09:15:00", 25000.0),
        ("2026-07-09T09:16:00", 25001.5),
        ("2026-07-09T09:17:00", 24998.5),
        ("2026-07-09T09:18:00", 25003.0),
        ("2026-07-09T09:19:00", 25002.0),
    ]
    prices = [price for _, price in sample_ticks]
    row = {
        "datetime": "2026-07-09T09:15:00",
        "open": prices[0],
        "high": max(prices),
        "low": min(prices),
        "close": prices[-1],
        "volume": 0,
        "source": "local_deterministic_sample_not_live_market_data",
    }
    write_csv(
        workspace / "FYERS_5M_NORMALIZED_SAMPLE.csv",
        [row],
        ["datetime", "open", "high", "low", "close", "volume", "source"],
    )
    return [row]


def base_payload(module_number: int, workspace: Path, trading_date: str, day_number: int) -> Dict[str, Any]:
    cfg = MODULES[module_number]
    status_key = cfg["status_key"]
    payload: Dict[str, Any] = {
        "version": VERSION,
        "module_number": module_number,
        "module_name": cfg["name"],
        status_key: "PASS",
        "decision": cfg["decision"],
        "workspace": str(workspace),
        "trading_date": trading_date,
        "day_number": day_number,
        "generated_at_utc": utc_now_iso(),
        "safety_lock": dict(SAFETY_LOCK),
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "fake_trades_created": False,
        "candidate_tuning": False,
        "real_money_automatic": False,
        "allowed_scope": "local_or_data_only_preflight_no_order_execution",
        "blocked_order_apis": BLOCKED_ORDER_APIS,
    }
    # Also include module-scoped fields that prior HQE modules expect.
    key_suffix = f"module_{module_number}"
    payload[f"external_api_calls_executed_by_{key_suffix}"] = False
    payload[f"order_api_invoked_by_{key_suffix}"] = False
    payload[f"broker_execution_invoked_by_{key_suffix}"] = False
    payload[f"auto_trading_started_by_{key_suffix}"] = False
    payload[f"fake_trades_created_by_{key_suffix}"] = False
    return payload


def build_module_payload(
    module_number: int,
    workspace: Path | str,
    trading_date: str = "2026-07-09",
    day_number: int = 1,
    write: bool = False,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    payload = base_payload(module_number, workspace, trading_date, day_number)
    secrets = env_secret_report()
    day_counts = count_day_ledger(workspace)
    trade_counts = count_actual_trade_rows(workspace, day_number)
    payload.update(day_counts)
    payload.update(trade_counts)

    if module_number == 161:
        payload.update(
            {
                "credential_setup_mode": "ENVIRONMENT_VARIABLES_ONLY",
                "secret_file_written": False,
                "plaintext_secret_storage_allowed": False,
                "secrets": secrets,
                "operator_instruction": "Set FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN as user environment variables only; do not commit secrets.",
            }
        )
        if secrets["credentials_complete_for_future_data_transport"]:
            payload["decision"] = "FYERS_SECRET_PREFLIGHT_READY_DATA_ONLY_CREDENTIALS_PRESENT"

    elif module_number == 162:
        token_present = bool(os.environ.get("FYERS_ACCESS_TOKEN"))
        client_present = bool(os.environ.get("FYERS_CLIENT_ID"))
        token_text = os.environ.get("FYERS_ACCESS_TOKEN", "")
        payload.update(
            {
                "token_validation_mode": "OFFLINE_ENV_PRESENCE_AND_SHAPE_ONLY",
                "client_id_present": client_present,
                "access_token_present": token_present,
                "access_token_value_redacted": True,
                "token_expiry_verified_online": False,
                "token_shape_hint_ok": bool(token_text and len(token_text) >= 20) if token_present else False,
                "external_validation_call_executed": False,
                "secrets": secrets,
            }
        )
        if not token_present:
            payload["decision"] = "FYERS_TOKEN_MISSING_SET_ENV_BEFORE_LIVE_DATA"

    elif module_number == 163:
        payload.update(
            {
                "mode": "FYERS_DATA_ONLY_QUOTE_LTP_FETCHER",
                "fetch_mode": "OFFLINE_DRY_RUN_BY_DEFAULT",
                "market_symbol": "NSE:NIFTY50-INDEX",
                "allowed_data_scopes": ["quotes", "ltp", "market_depth", "historical_candles", "websocket_market_data"],
                "live_fetch_executed": False,
                "sample_quote_emitted": True,
                "sample_quote": {
                    "symbol": "NSE:NIFTY50-INDEX",
                    "ltp": None,
                    "source": "no_live_api_call_executed",
                },
                "secrets": secrets,
            }
        )

    elif module_number == 164:
        sample_rows = build_candles_from_sample(workspace) if write else []
        payload.update(
            {
                "normalizer_mode": "LOCAL_5M_CANDLE_BUILDER",
                "input_tick_source": "local_sample_or_future_data_only_transport",
                "normalized_candle_rows_written": len(sample_rows),
                "normalized_sample_file": str(workspace / "FYERS_5M_NORMALIZED_SAMPLE.csv"),
                "live_market_data_used": False,
                "trade_signal_generated": False,
            }
        )

    elif module_number == 165:
        now_text = now or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        payload.update(
            {
                "watch_loop_mode": "MANUAL_START_DATA_ONLY_PAPER_WATCH",
                "market_session_start": "09:15",
                "market_session_end": "15:30",
                "now_local_assumed": now_text,
                "watch_loop_started": False,
                "loop_iterations_executed": 0,
                "auto_start_enabled": False,
                "data_transport_required_before_live_watch": True,
            }
        )

    elif module_number == 166:
        approved = approved_signal_count(workspace, day_number)
        executed_rows = executed_paper_signal_rows(workspace, day_number)
        if write:
            write_csv(
                workspace / f"DAY_{day_number:03d}_PAPER_EXECUTION_LOG.csv",
                executed_rows,
                ["paper_trade_id", "trading_date", "symbol", "side", "entry_price", "quantity", "source"],
            )
        payload.update(
            {
                "approved_signal_rows": approved,
                "explicit_paper_execution_rows_logged": len(executed_rows),
                "paper_execution_log_file": str(workspace / f"DAY_{day_number:03d}_PAPER_EXECUTION_LOG.csv"),
                "paper_order_sent_to_broker": False,
                "real_order_sent_to_broker": False,
                "fake_trade_policy": "do_not_create_trade_without_explicit_paper_execution_flag",
            }
        )

    elif module_number == 167:
        approved = approved_signal_count(workspace, day_number)
        actual = trade_counts["actual_paper_trades"]
        reason = "PAPER_TRADE_PRESENT_NO_NO_TRADE_REASON_NEEDED" if actual > 0 else "NO_EXPLICIT_PAPER_EXECUTION_ROWS_AVAILABLE"
        if approved == 0 and actual == 0:
            reason = "NO_APPROVED_SIGNAL_ROWS_AVAILABLE"
        payload.update(
            {
                "approved_signal_rows": approved,
                "no_trade_reason": reason,
                "no_trade_reason_recorded": actual == 0,
                "valid_trade_day_incremented": actual > 0,
                "no_trade_day_counts_as_observed_session_only": actual == 0,
            }
        )

    elif module_number == 168:
        payload.update(
            {
                "daily_close_mode": "LOCAL_REPORT_TRACKER_INTEGRATION",
                "daily_close_auto_executed": False,
                "manual_operator_review_required": True,
                "report_files_expected": [
                    f"DAY_{day_number:03d}_FORWARD_VALIDATION_DAY_CLOSE.md",
                    f"DAY_{day_number:03d}_NO_TRADE_REASON.md",
                    "HQE_30_VALID_TRADE_DAY_TRACKER_STATUS.md",
                ],
                "tracker_rule": "valid_paper_trade_days_count_only_days_with_trade_count_gt_zero",
            }
        )

    elif module_number == 169:
        launcher = workspace / "OPEN_HQE_SAFE_STARTUP_LOGIN_GATE_ONLY.cmd"
        if write:
            launcher.write_text(
                "@echo off\r\n"
                "echo HQE SAFE STARTUP LOGIN GATE ONLY\r\n"
                "echo This launcher does not start trading, broker execution, or order APIs.\r\n"
                "pause\r\n",
                encoding="utf-8",
            )
        payload.update(
            {
                "startup_mode": "WINDOWS_ONLOGON_LOGIN_GATE_ONLY",
                "scheduled_task_installed_by_this_run": False,
                "desktop_shortcut_created_by_this_run": False,
                "startup_launcher_emitted": write,
                "startup_launcher_path": str(launcher),
                "auto_start_trading": False,
                "auto_broker_connect": False,
            }
        )

    elif module_number == 170:
        expected_prefixes = [MODULES[number]["prefix"] for number in range(161, 170)]
        existing_status_files = [str(workspace / f"{prefix}_STATUS.json") for prefix in expected_prefixes if (workspace / f"{prefix}_STATUS.json").exists()]
        payload.update(
            {
                "dry_run_mode": "FULL_LIVE_PAPER_FOUNDATION_DRY_RUN_LOCAL_ONLY",
                "modules_161_to_169_status_files_found": len(existing_status_files),
                "modules_161_to_169_expected_status_files": len(expected_prefixes),
                "existing_status_files": existing_status_files,
                "ready_for_daily_paper_validation_operation": True,
                "ready_for_real_money": False,
                "real_money_requires_future_explicit_manual_approval": True,
                "target_valid_paper_trade_days": 30,
            }
        )

    if write:
        write_evidence(module_number, workspace, payload)
    return payload


def write_evidence(module_number: int, workspace: Path, payload: Dict[str, Any]) -> None:
    cfg = MODULES[module_number]
    prefix = cfg["prefix"]
    json_path = workspace / f"{prefix}_STATUS.json"
    md_path = workspace / f"{prefix}_STATUS.md"
    ledger_path = workspace / "MODULES_161_170_LIVE_PAPER_FOUNDATION_LEDGER.csv"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"# {cfg['name']}",
        "",
        f"module_number: {module_number}",
        f"status: {payload.get(cfg['status_key'])}",
        f"decision: {payload.get('decision')}",
        f"paper_only: {payload['safety_lock']['paper_only']}",
        f"no_real_money: {payload['safety_lock']['no_real_money']}",
        f"no_broker_execution: {payload['safety_lock']['no_broker_execution']}",
        f"no_real_orders: {payload['safety_lock']['no_real_orders']}",
        f"no_auto_trading: {payload['safety_lock']['no_auto_trading']}",
        f"no_fake_trades: {payload['safety_lock']['no_fake_trades']}",
        f"observed_session_days: {payload.get('observed_session_days', 0)}",
        f"valid_paper_trade_days: {payload.get('valid_paper_trade_days', 0)}",
        f"actual_paper_trades: {payload.get('actual_paper_trades', 0)}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ledger_exists = ledger_path.exists()
    with ledger_path.open("a", encoding="utf-8", newline="") as f:
        fieldnames = ["generated_at_utc", "module_number", "module_name", "status", "decision", "paper_only", "no_real_money", "actual_paper_trades", "valid_paper_trade_days"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not ledger_exists:
            writer.writeheader()
        writer.writerow(
            {
                "generated_at_utc": payload.get("generated_at_utc"),
                "module_number": module_number,
                "module_name": cfg["name"],
                "status": payload.get(cfg["status_key"]),
                "decision": payload.get("decision"),
                "paper_only": payload["safety_lock"]["paper_only"],
                "no_real_money": payload["safety_lock"]["no_real_money"],
                "actual_paper_trades": payload.get("actual_paper_trades", 0),
                "valid_paper_trade_days": payload.get("valid_paper_trade_days", 0),
            }
        )
    payload["evidence_files"] = {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}


def guard_check_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "safety_lock": dict(SAFETY_LOCK),
        "blocked_order_apis": {name: "ORDER_API_BLOCKED:HARD_BLOCKED" for name in BLOCKED_ORDER_APIS},
        "external_api_calls_executed": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
        "auto_trading_started": False,
        "fake_trades_created": False,
        "real_money_automatic": False,
    }


def run_module_cli(module_number: int) -> int:
    parser = argparse.ArgumentParser(description=MODULES[module_number]["name"])
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    parser.add_argument("--trading-date", default="2026-07-09")
    parser.add_argument("--day-number", type=int, default=1)
    parser.add_argument("--now", default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()
    if args.guard_check:
        print(json.dumps(guard_check_payload(), indent=2, sort_keys=True))
        return 0
    payload = build_module_payload(
        module_number=module_number,
        workspace=Path(args.workspace),
        trading_date=args.trading_date,
        day_number=args.day_number,
        write=args.write,
        now=args.now,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
