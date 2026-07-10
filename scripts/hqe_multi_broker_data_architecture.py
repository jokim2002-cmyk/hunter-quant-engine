from __future__ import annotations

import argparse
import json
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


VERSION = "HQE_MULTI_BROKER_DATA_ARCHITECTURE_V1"

SAFETY_LOCK: Dict[str, bool] = {
    "paper_only": True,
    "data_only": True,
    "manual_operator_control": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_profitability_claim": True,
    "order_api_hard_blocked": True,
}

BLOCKED_ORDER_ACTIONS = (
    "place_order",
    "modify_order",
    "cancel_order",
    "exit_position",
    "exit_positions",
    "convert_position",
    "place_gtt_order",
    "modify_gtt_order",
    "cancel_gtt_order",
    "place_basket_order",
    "place_basket_orders",
)


@dataclass(frozen=True)
class BrokerDefinition:
    broker_id: str
    display_name: str
    short_name: str
    data_adapter_status: str
    credential_fields: tuple[str, ...]
    supports_live_quotes: bool
    supports_historical_candles: bool
    execution_enabled: bool = False
    order_methods_available: bool = False


BROKER_REGISTRY: Dict[str, BrokerDefinition] = {
    "fyers": BrokerDefinition(
        broker_id="fyers",
        display_name="Fyers",
        short_name="FY",
        data_adapter_status="AVAILABLE_DATA_ONLY",
        credential_fields=("client_id", "access_token"),
        supports_live_quotes=True,
        supports_historical_candles=True,
    ),
    "zerodha": BrokerDefinition(
        broker_id="zerodha",
        display_name="Zerodha",
        short_name="ZE",
        data_adapter_status="ARCHITECTURE_READY_NOT_CONNECTED",
        credential_fields=("api_key", "access_token"),
        supports_live_quotes=False,
        supports_historical_candles=False,
    ),
    "angel_one": BrokerDefinition(
        broker_id="angel_one",
        display_name="Angel One",
        short_name="AO",
        data_adapter_status="ARCHITECTURE_READY_NOT_CONNECTED",
        credential_fields=("api_key", "client_code", "session_token"),
        supports_live_quotes=False,
        supports_historical_candles=False,
    ),
    "upstox": BrokerDefinition(
        broker_id="upstox",
        display_name="Upstox",
        short_name="UP",
        data_adapter_status="ARCHITECTURE_READY_NOT_CONNECTED",
        credential_fields=("client_id", "access_token"),
        supports_live_quotes=False,
        supports_historical_candles=False,
    ),
    "groww": BrokerDefinition(
        broker_id="groww",
        display_name="Groww",
        short_name="GR",
        data_adapter_status="ARCHITECTURE_READY_NOT_CONNECTED",
        credential_fields=("api_key", "access_token"),
        supports_live_quotes=False,
        supports_historical_candles=False,
    ),
    "dhan": BrokerDefinition(
        broker_id="dhan",
        display_name="Dhan",
        short_name="DH",
        data_adapter_status="ARCHITECTURE_READY_NOT_CONNECTED",
        credential_fields=("client_id", "access_token"),
        supports_live_quotes=False,
        supports_historical_candles=False,
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DataOnlyBrokerAdapter(ABC):
    """Common contract for market-data adapters.

    Deliberately contains no order placement, modification, cancellation,
    position, holdings, funds or execution methods.
    """

    definition: BrokerDefinition

    @abstractmethod
    def credential_status(
        self,
        credentials: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def connection_test(
        self,
        credentials: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def market_data_status(self, workspace: Path) -> Dict[str, Any]:
        raise NotImplementedError


class RegistryDataOnlyAdapter(DataOnlyBrokerAdapter):
    def __init__(self, definition: BrokerDefinition) -> None:
        self.definition = definition

    def _resolved_credentials(
        self,
        credentials: Optional[Mapping[str, str]],
    ) -> Dict[str, str]:
        provided = dict(credentials or {})
        resolved: Dict[str, str] = {}

        for field_name in self.definition.credential_fields:
            supplied = str(provided.get(field_name, "")).strip()
            if supplied:
                resolved[field_name] = supplied
                continue

            env_name = (
                f"{self.definition.broker_id}_{field_name}"
                .upper()
                .replace("-", "_")
            )
            value = os.environ.get(env_name, "").strip()

            if self.definition.broker_id == "fyers":
                aliases = {
                    "client_id": "FYERS_CLIENT_ID",
                    "access_token": "FYERS_ACCESS_TOKEN",
                }
                value = os.environ.get(aliases.get(field_name, env_name), "").strip()

            resolved[field_name] = value

        return resolved

    def credential_status(
        self,
        credentials: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        resolved = self._resolved_credentials(credentials)
        missing = [name for name, value in resolved.items() if not value]

        return {
            "broker_id": self.definition.broker_id,
            "display_name": self.definition.display_name,
            "required_fields": list(self.definition.credential_fields),
            "present_field_count": len(resolved) - len(missing),
            "missing_fields": missing,
            "credentials_complete": not missing,
            "secret_values_redacted": True,
            "plaintext_secret_storage_allowed": False,
        }

    def connection_test(
        self,
        credentials: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        credential_state = self.credential_status(credentials)

        if self.definition.broker_id != "fyers":
            status = "ADAPTER_NOT_IMPLEMENTED"
            message = (
                f"{self.definition.display_name} data adapter architecture is ready, "
                "but live connection implementation is not enabled yet."
            )
        elif not credential_state["credentials_complete"]:
            status = "WAITING_FOR_CREDENTIALS"
            message = "Fyers data-only credentials are incomplete."
        else:
            status = "READY_FOR_EXISTING_FYERS_DATA_ONLY_TEST"
            message = (
                "Credentials are present. The existing HQE Fyers data-only "
                "fetcher remains the approved connection test."
            )

        return {
            "broker_id": self.definition.broker_id,
            "status": status,
            "message": message,
            "network_request_executed": False,
            "broker_execution_invoked": False,
            "order_api_invoked": False,
            "credential_status": credential_state,
        }

    def market_data_status(self, workspace: Path) -> Dict[str, Any]:
        if self.definition.broker_id != "fyers":
            return {
                "broker_id": self.definition.broker_id,
                "status": "NOT_IMPLEMENTED",
                "data_ready": False,
                "source": "broker_registry",
            }

        candidates = (
            workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json",
            workspace / "MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS.json",
            workspace / "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json",
        )

        found = [str(path) for path in candidates if path.exists()]
        data_ready = False

        for path in candidates:
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue

            if payload.get("data_only_connection_ready") is True:
                data_ready = True

            health = payload.get("data_health", {})
            if isinstance(health, dict) and health.get("data_only_connection_ready") is True:
                data_ready = True

            history = payload.get("history_result", {})
            if isinstance(history, dict) and int(history.get("rows", 0) or 0) > 0:
                data_ready = True

        return {
            "broker_id": "fyers",
            "status": "DATA_READY" if data_ready else "WAITING_FOR_DATA_TEST",
            "data_ready": data_ready,
            "evidence_files_found": found,
            "source": "existing_hqe_fyers_data_only_evidence",
        }


def get_adapter(broker_id: str) -> DataOnlyBrokerAdapter:
    key = broker_id.strip().lower()
    if key not in BROKER_REGISTRY:
        raise KeyError(f"Unsupported broker: {broker_id}")
    return RegistryDataOnlyAdapter(BROKER_REGISTRY[key])


def architecture_payload(workspace: Path) -> Dict[str, Any]:
    brokers: List[Dict[str, Any]] = []

    for definition in BROKER_REGISTRY.values():
        adapter = get_adapter(definition.broker_id)
        brokers.append(
            {
                **asdict(definition),
                "credential_status": adapter.credential_status(),
                "connection_test": adapter.connection_test(),
                "market_data_status": adapter.market_data_status(workspace),
            }
        )

    return {
        "version": VERSION,
        "generated_at_utc": utc_now(),
        "workspace": str(workspace),
        "architecture_status": "PASS",
        "decision": "MULTI_BROKER_DATA_ONLY_ARCHITECTURE_READY",
        "broker_count": len(brokers),
        "brokers": brokers,
        "blocked_order_actions": {
            action: "HARD_BLOCKED" for action in BLOCKED_ORDER_ACTIONS
        },
        "safety_lock": SAFETY_LOCK,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def guard_payload() -> Dict[str, Any]:
    adapter_public_methods = sorted(
        name
        for name in dir(DataOnlyBrokerAdapter)
        if not name.startswith("_")
    )

    forbidden_found = sorted(
        name for name in adapter_public_methods if name in BLOCKED_ORDER_ACTIONS
    )

    return {
        "version": VERSION,
        "guard_check_status": "PASS" if not forbidden_found else "FAIL",
        "broker_count": len(BROKER_REGISTRY),
        "broker_ids": list(BROKER_REGISTRY),
        "adapter_public_methods": adapter_public_methods,
        "forbidden_order_methods_found": forbidden_found,
        "blocked_order_actions": {
            action: "HARD_BLOCKED" for action in BLOCKED_ORDER_ACTIONS
        },
        "safety_lock": SAFETY_LOCK,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HQE multi-broker data-only architecture"
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace)

    if args.guard_check:
        payload = guard_payload()
    else:
        payload = architecture_payload(workspace)

    if args.write:
        workspace.mkdir(parents=True, exist_ok=True)
        output = workspace / "HQE_MULTI_BROKER_DATA_ARCHITECTURE_STATUS.json"
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload["status_file"] = str(output)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("guard_check_status", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
