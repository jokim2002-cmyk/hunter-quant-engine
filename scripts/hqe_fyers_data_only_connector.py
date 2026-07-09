"""HQE Fyers data-only connector foundation.

Module 148 safety scope:
- Data-only connector shell/foundation only.
- No broker execution.
- No order placement, modification, cancellation, exit, or auto trading.
- No option selling.
- No real money.
- No plaintext secrets in the repo or generated local config.
- No live external API call is made by this module unless a future module explicitly
  adds a safe, data-only transport layer.

This module intentionally separates market-data readiness from broker/order
execution. It can write local evidence/config files, but it never sends orders.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

VERSION = "MODULE_148_FYERS_DATA_ONLY_CONNECTOR_V1"
DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_LOCAL_CONFIG = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FYERS_DATA_ONLY\fyers_data_only_config.json")
DEFAULT_STATUS_JSON = "FYERS_DATA_ONLY_CONNECTOR_STATUS.json"
DEFAULT_STATUS_MD = "FYERS_DATA_ONLY_CONNECTOR_STATUS.md"
DEFAULT_STATUS_LEDGER = "FYERS_DATA_ONLY_CONNECTOR_LEDGER.csv"

ENV_CLIENT_ID = "FYERS_CLIENT_ID"
ENV_ACCESS_TOKEN = "FYERS_ACCESS_TOKEN"
ENV_REDIRECT_URI = "FYERS_REDIRECT_URI"
ENV_APP_ID = "FYERS_APP_ID"

DATA_ONLY_SCOPES: List[str] = [
    "quotes",
    "ltp",
    "market_depth",
    "historical_candles",
    "websocket_market_data",
]

BLOCKED_ORDER_APIS: List[str] = [
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

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
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


class BrokerExecutionBlockedError(RuntimeError):
    """Raised whenever any broker/order/account execution path is attempted."""


@dataclass(frozen=True)
class FyersDataOnlyConfig:
    market_symbol: str = "NSE:NIFTY50-INDEX"
    data_interval: str = "5m"
    market_session_start: str = "09:15"
    market_session_end: str = "15:30"
    credential_source: str = "environment_variables_only"
    allow_order_api: bool = False
    allow_broker_execution: bool = False
    allow_auto_trading: bool = False
    allow_option_selling: bool = False

    def validate(self) -> None:
        if not self.market_symbol.strip():
            raise ValueError("market_symbol is required")
        if self.allow_order_api:
            raise BrokerExecutionBlockedError("ORDER_API_BLOCKED: allow_order_api must remain false")
        if self.allow_broker_execution:
            raise BrokerExecutionBlockedError("BROKER_EXECUTION_BLOCKED: allow_broker_execution must remain false")
        if self.allow_auto_trading:
            raise BrokerExecutionBlockedError("AUTO_TRADING_BLOCKED: allow_auto_trading must remain false")
        if self.allow_option_selling:
            raise BrokerExecutionBlockedError("OPTION_SELLING_BLOCKED: allow_option_selling must remain false")

    def to_safe_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "version": VERSION,
            "mode": "DATA_ONLY",
            "market_symbol": self.market_symbol,
            "data_interval": self.data_interval,
            "market_session_start": self.market_session_start,
            "market_session_end": self.market_session_end,
            "credential_source": self.credential_source,
            "allowed_data_scopes": list(DATA_ONLY_SCOPES),
            "blocked_order_apis": list(BLOCKED_ORDER_APIS),
            "allow_order_api": False,
            "allow_broker_execution": False,
            "allow_auto_trading": False,
            "allow_option_selling": False,
            "secrets_included": False,
        }


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    ensure_dir(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def append_csv_row(path: Path, row: Dict[str, Any], fieldnames: Iterable[str]) -> None:
    ensure_dir(path)
    fieldnames = list(fieldnames)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def secret_presence_snapshot(env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    env = os.environ if env is None else env
    required = [ENV_CLIENT_ID, ENV_ACCESS_TOKEN]
    optional = [ENV_REDIRECT_URI, ENV_APP_ID]
    present_required = [name for name in required if bool(env.get(name))]
    missing_required = [name for name in required if not env.get(name)]
    present_optional = [name for name in optional if bool(env.get(name))]
    return {
        "secret_values_redacted": True,
        "required_env_names": required,
        "optional_env_names": optional,
        "present_required_env_count": len(present_required),
        "missing_required_env_names": missing_required,
        "present_optional_env_count": len(present_optional),
        "credentials_complete_for_future_data_transport": len(missing_required) == 0,
    }


def assert_order_api_blocked(action: str) -> None:
    normalized = (action or "").strip().lower()
    if not normalized:
        normalized = "unknown_order_or_account_action"
    raise BrokerExecutionBlockedError(
        f"ORDER_API_BLOCKED:{normalized}: Module 148 is data-only; "
        "broker execution, real orders, auto trading, and option selling are disabled."
    )


class FyersDataOnlyConnector:
    """Safe shell for future Fyers market-data access.

    The class exposes only status/preflight and explicit hard-block methods for
    order/account paths. It does not import or call the Fyers SDK in Module 148.
    """

    def __init__(self, config: Optional[FyersDataOnlyConfig] = None, *, env: Optional[Dict[str, str]] = None) -> None:
        self.config = config or FyersDataOnlyConfig()
        self.config.validate()
        self.env = os.environ if env is None else env

    def status(self, *, require_credentials: bool = False) -> Dict[str, Any]:
        secrets = secret_presence_snapshot(self.env)
        credentials_complete = bool(secrets["credentials_complete_for_future_data_transport"])
        if require_credentials and not credentials_complete:
            readiness = "WAITING_FOR_FYERS_DATA_CREDENTIALS"
        elif credentials_complete:
            readiness = "DATA_ONLY_CREDENTIALS_PRESENT_TRANSPORT_NOT_STARTED"
        else:
            readiness = "DATA_ONLY_SHELL_READY_NO_CREDENTIALS"
        return {
            "version": VERSION,
            "connector_status": "PASS",
            "mode": "DATA_ONLY",
            "readiness_decision": readiness,
            "external_api_calls_executed": False,
            "fyers_sdk_imported": False,
            "live_data_transport_started": False,
            "order_api_block_status": "HARD_BLOCKED",
            "broker_execution_block_status": "HARD_BLOCKED",
            "config": self.config.to_safe_dict(),
            "secrets": secrets,
            "safety_lock": dict(SAFETY_LOCK),
        }

    def preflight(self, *, require_credentials: bool = False) -> Dict[str, Any]:
        status = self.status(require_credentials=require_credentials)
        missing = list(status["secrets"]["missing_required_env_names"])
        warnings: List[str] = []
        if missing:
            warnings.append("Fyers data credentials are not present in environment variables; live data transport remains unavailable.")
        payload = {
            **status,
            "preflight_status": "PASS",
            "preflight_time_utc": utc_now_iso(),
            "warnings": warnings,
            "allowed_next_step": "future_data_only_transport_after_manual_secret_setup",
            "blocked_next_steps": list(BLOCKED_ORDER_APIS),
        }
        if require_credentials and missing:
            payload["preflight_status"] = "HOLD_WAITING_FOR_DATA_CREDENTIALS"
        return payload

    def connect_data_transport(self) -> Dict[str, Any]:
        """Do not start live networking in Module 148; return a safe hold."""
        status = self.status(require_credentials=True)
        status.update(
            {
                "connect_attempt_status": "NOT_STARTED_BY_MODULE_148",
                "reason": "Module 148 creates a data-only shell; future module may add safe data-only Fyers transport.",
                "external_api_calls_executed": False,
                "live_data_transport_started": False,
            }
        )
        return status

    def place_order(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("place_order")

    def modify_order(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("modify_order")

    def cancel_order(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("cancel_order")

    def exit_positions(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("exit_positions")

    def place_basket_orders(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("place_basket_orders")

    def orderbook(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("orderbook")

    def tradebook(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("tradebook")

    def positions(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("positions")

    def holdings(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("holdings")

    def funds(self, *_: Any, **__: Any) -> None:
        assert_order_api_blocked("funds")


def build_config(
    *,
    market_symbol: str = "NSE:NIFTY50-INDEX",
    data_interval: str = "5m",
    market_session_start: str = "09:15",
    market_session_end: str = "15:30",
) -> FyersDataOnlyConfig:
    return FyersDataOnlyConfig(
        market_symbol=market_symbol,
        data_interval=data_interval,
        market_session_start=market_session_start,
        market_session_end=market_session_end,
    )


def write_local_config(path: Path, config: FyersDataOnlyConfig) -> Dict[str, Any]:
    payload = {
        **config.to_safe_dict(),
        "created_at_utc": utc_now_iso(),
        "safety_lock": dict(SAFETY_LOCK),
        "note": "No secrets are stored here. Set FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN in environment variables only.",
    }
    serialized = json.dumps(payload, sort_keys=True)
    if "access_token" in serialized.lower() and "FYERS_ACCESS_TOKEN" not in serialized:
        raise ValueError("unsafe config serialization detected")
    atomic_write_json(path, payload)
    return payload


def render_markdown(payload: Dict[str, Any]) -> str:
    secrets = payload.get("secrets", {})
    config = payload.get("config", {})
    warnings = payload.get("warnings", [])
    lines = [
        "# HQE Fyers Data-Only Connector Status",
        "",
        f"- version: {payload.get('version')}",
        f"- connector_status: {payload.get('connector_status')}",
        f"- preflight_status: {payload.get('preflight_status', '')}",
        f"- readiness_decision: {payload.get('readiness_decision')}",
        f"- mode: {payload.get('mode')}",
        f"- market_symbol: {config.get('market_symbol')}",
        f"- external_api_calls_executed: {payload.get('external_api_calls_executed')}",
        f"- live_data_transport_started: {payload.get('live_data_transport_started')}",
        f"- order_api_block_status: {payload.get('order_api_block_status')}",
        f"- broker_execution_block_status: {payload.get('broker_execution_block_status')}",
        f"- credentials_complete_for_future_data_transport: {secrets.get('credentials_complete_for_future_data_transport')}",
        f"- missing_required_env_names: {', '.join(secrets.get('missing_required_env_names', [])) or 'NONE'}",
        "",
        "## Safety Lock",
    ]
    for key, value in payload.get("safety_lock", {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Blocked Order/Account APIs")
    for name in BLOCKED_ORDER_APIS:
        lines.append(f"- {name}: HARD_BLOCKED")
    if warnings:
        lines.append("")
        lines.append("## Warnings")
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    lines.append("No real money, no broker execution, no real orders, no auto trading, no option selling, no profitability claim.")
    return "\n".join(lines) + "\n"


def write_workspace_evidence(workspace: Path, payload: Dict[str, Any]) -> Dict[str, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    json_path = workspace / DEFAULT_STATUS_JSON
    md_path = workspace / DEFAULT_STATUS_MD
    ledger_path = workspace / DEFAULT_STATUS_LEDGER
    atomic_write_json(json_path, payload)
    atomic_write_text(md_path, render_markdown(payload))
    append_csv_row(
        ledger_path,
        {
            "created_at_utc": payload.get("preflight_time_utc") or utc_now_iso(),
            "version": payload.get("version"),
            "connector_status": payload.get("connector_status"),
            "preflight_status": payload.get("preflight_status", ""),
            "readiness_decision": payload.get("readiness_decision"),
            "mode": payload.get("mode"),
            "external_api_calls_executed": payload.get("external_api_calls_executed"),
            "live_data_transport_started": payload.get("live_data_transport_started"),
            "order_api_block_status": payload.get("order_api_block_status"),
            "broker_execution_block_status": payload.get("broker_execution_block_status"),
        },
        [
            "created_at_utc",
            "version",
            "connector_status",
            "preflight_status",
            "readiness_decision",
            "mode",
            "external_api_calls_executed",
            "live_data_transport_started",
            "order_api_block_status",
            "broker_execution_block_status",
        ],
    )
    return {"json": str(json_path), "markdown": str(md_path), "ledger": str(ledger_path)}


def guard_check_payload() -> Dict[str, Any]:
    blocked: Dict[str, str] = {}
    for name in BLOCKED_ORDER_APIS:
        try:
            assert_order_api_blocked(name)
        except BrokerExecutionBlockedError as exc:
            blocked[name] = str(exc).split(":", 2)[0] + ":HARD_BLOCKED"
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "blocked_order_apis": blocked,
        "safety_lock": dict(SAFETY_LOCK),
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQE Fyers data-only connector foundation")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="Forward validation workspace for evidence files")
    parser.add_argument("--local-config", default=str(DEFAULT_LOCAL_CONFIG), help="Local data-only config file outside repo")
    parser.add_argument("--market-symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--data-interval", default="5m")
    parser.add_argument("--session-start", default="09:15")
    parser.add_argument("--session-end", default="15:30")
    parser.add_argument("--status", action="store_true", help="Print data-only connector status")
    parser.add_argument("--preflight", action="store_true", help="Run safe local preflight without external API calls")
    parser.add_argument("--require-env", action="store_true", help="Require FYERS env variables for future live data transport readiness")
    parser.add_argument("--write", action="store_true", help="Write workspace evidence for status/preflight")
    parser.add_argument("--write-config", action="store_true", help="Write safe local config outside repo")
    parser.add_argument("--guard-check", action="store_true", help="Verify order/account API guards are hard-blocked")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    config = build_config(
        market_symbol=args.market_symbol,
        data_interval=args.data_interval,
        market_session_start=args.session_start,
        market_session_end=args.session_end,
    )
    connector = FyersDataOnlyConnector(config)

    if args.write_config:
        payload = write_local_config(Path(args.local_config), config)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.guard_check:
        payload = guard_check_payload()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.preflight:
        payload = connector.preflight(require_credentials=args.require_env)
    else:
        payload = connector.status(require_credentials=args.require_env)

    if args.write:
        payload["workspace"] = str(Path(args.workspace))
        payload["evidence_files"] = write_workspace_evidence(Path(args.workspace), payload)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
