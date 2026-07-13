from __future__ import annotations

import argparse
import csv
import inspect
import json
import os
import re
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

MODULE_VERSION = "HQE_FYERS_OPTION_CHAIN_DATA_ONLY_V1"
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"
IST = ZoneInfo("Asia/Kolkata")

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
}

CSV_FIELDS = (
    "generated_at_utc",
    "trading_date",
    "underlying_symbol",
    "symbol",
    "option_type",
    "signal_side",
    "strike_price",
    "ltp",
    "bid",
    "ask",
    "oi",
    "volume",
    "expiry_timestamp",
    "dte",
    "source",
)


class OptionChainDataError(RuntimeError):
    pass


def utc_now_text() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def ist_today_text() -> str:
    return datetime.now(IST).date().isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    numeric = _number(value)
    return None if numeric is None else int(numeric)


def _first(mapping: dict[str, Any], names: tuple[str, ...]) -> Any:
    lowered = {
        str(key).strip().lower(): value
        for key, value in mapping.items()
    }
    for name in names:
        if name.lower() in lowered:
            value = lowered[name.lower()]
            if value not in (None, ""):
                return value
    return None


def infer_option_type(row: dict[str, Any]) -> str:
    explicit = _text(
        _first(
            row,
            (
                "option_type",
                "optiontype",
                "right",
                "type",
            ),
        )
    ).upper()

    if explicit in {"CE", "CALL", "CALL_OPTION"}:
        return "CE"
    if explicit in {"PE", "PUT", "PUT_OPTION"}:
        return "PE"

    symbol = _text(
        _first(
            row,
            (
                "symbol",
                "tradingsymbol",
                "option_symbol",
            ),
        )
    ).upper()

    if symbol.endswith("CE"):
        return "CE"
    if symbol.endswith("PE"):
        return "PE"
    return ""


def signal_side(option_type: str) -> str:
    if option_type == "CE":
        return "CE_BUY"
    if option_type == "PE":
        return "PE_BUY"
    return "NO_TRADE"


def _parse_expiry_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None

    if re.fullmatch(r"\d{10,13}", text):
        try:
            epoch = int(text)
            if len(text) == 13:
                epoch //= 1000
            return datetime.fromtimestamp(
                epoch,
                tz=timezone.utc,
            ).astimezone(IST).date()
        except (OverflowError, OSError, ValueError):
            return None

    match = re.search(
        r"(?<!\d)(20\d{2})[-_/](\d{2})[-_/](\d{2})(?!\d)",
        text,
    )
    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            return None

    for pattern in (
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _dte(expiry_value: Any, trading_date: str) -> int | None:
    expiry = _parse_expiry_date(expiry_value)
    try:
        trading_day = date.fromisoformat(trading_date)
    except ValueError:
        return None
    if expiry is None:
        return None
    return (expiry - trading_day).days


def extract_chain_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("data")
    if not isinstance(data, dict):
        return []

    for key in (
        "optionsChain",
        "optionChain",
        "options_chain",
        "option_chain",
    ):
        rows = data.get(key)
        if isinstance(rows, list):
            return [
                row
                for row in rows
                if isinstance(row, dict)
            ]
    return []


def extract_expiry_data(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("data")
    if not isinstance(data, dict):
        return []

    for key in (
        "expiryData",
        "expiry_data",
        "expiries",
    ):
        rows = data.get(key)
        if isinstance(rows, list):
            return [
                row
                for row in rows
                if isinstance(row, dict)
            ]
    return []


def selected_expiry_value(
    response: dict[str, Any],
    requested_timestamp: str,
) -> Any:
    if requested_timestamp.strip():
        return requested_timestamp.strip()

    expiries = extract_expiry_data(response)
    if not expiries:
        return ""

    first = expiries[0]
    return _first(
        first,
        (
            "expiry",
            "expiry_timestamp",
            "timestamp",
            "date",
        ),
    )


def normalize_chain(
    response: dict[str, Any],
    *,
    underlying_symbol: str,
    trading_date: str,
    requested_expiry_timestamp: str = "",
    generated_at_utc: str | None = None,
) -> list[dict[str, Any]]:
    generated = generated_at_utc or utc_now_text()
    expiry_default = selected_expiry_value(
        response,
        requested_expiry_timestamp,
    )
    normalized: list[dict[str, Any]] = []

    for row in extract_chain_rows(response):
        option_type = infer_option_type(row)
        if option_type not in {"CE", "PE"}:
            continue

        symbol = _text(
            _first(
                row,
                (
                    "symbol",
                    "tradingsymbol",
                    "option_symbol",
                ),
            )
        )
        if not symbol:
            continue

        expiry_value = _first(
            row,
            (
                "expiry",
                "expiry_timestamp",
                "expirydate",
                "expiry_date",
            ),
        )
        if expiry_value in (None, ""):
            expiry_value = expiry_default

        normalized.append(
            {
                "generated_at_utc": generated,
                "trading_date": trading_date,
                "underlying_symbol": underlying_symbol,
                "symbol": symbol,
                "option_type": option_type,
                "signal_side": signal_side(option_type),
                "strike_price": _number(
                    _first(
                        row,
                        (
                            "strike_price",
                            "strikeprice",
                            "strike",
                        ),
                    )
                ),
                "ltp": _number(
                    _first(
                        row,
                        (
                            "ltp",
                            "last_price",
                            "last_traded_price",
                        ),
                    )
                ),
                "bid": _number(
                    _first(
                        row,
                        (
                            "bid",
                            "bid_price",
                            "bidprice",
                        ),
                    )
                ),
                "ask": _number(
                    _first(
                        row,
                        (
                            "ask",
                            "ask_price",
                            "askprice",
                        ),
                    )
                ),
                "oi": _number(
                    _first(
                        row,
                        (
                            "oi",
                            "open_interest",
                        ),
                    )
                ),
                "volume": _number(
                    _first(
                        row,
                        (
                            "volume",
                            "vol",
                        ),
                    )
                ),
                "expiry_timestamp": _text(expiry_value),
                "dte": _dte(expiry_value, trading_date),
                "source": "FYERS_OPTIONCHAIN_DATA_ONLY",
            }
        )

    normalized.sort(
        key=lambda item: (
            item["strike_price"]
            if item["strike_price"] is not None
            else float("inf"),
            item["option_type"],
            item["symbol"],
        )
    )
    return normalized


def chain_readiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(
        str(row.get("option_type", ""))
        for row in rows
        if row.get("option_type") in {"CE", "PE"}
    )
    ce_count = counts.get("CE", 0)
    pe_count = counts.get("PE", 0)

    valid_ltp = sum(
        1
        for row in rows
        if isinstance(row.get("ltp"), (int, float))
        and float(row["ltp"]) > 0
    )
    both_sides = ce_count > 0 and pe_count > 0

    return {
        "status": (
            "BOTH_SIDES_READY"
            if both_sides
            else "OPTION_CHAIN_INCOMPLETE"
        ),
        "row_count": len(rows),
        "ce_count": ce_count,
        "pe_count": pe_count,
        "valid_ltp_count": valid_ltp,
        "both_sides_ready": both_sides,
    }


def safe_response_summary(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "s": response.get("s"),
        "code": response.get("code"),
        "message": _text(
            response.get("message")
            or response.get("msg")
        )[:300],
        "chain_row_count": len(extract_chain_rows(response)),
        "expiry_count": len(extract_expiry_data(response)),
    }


def build_fyers_client(
    *,
    client_id: str,
    access_token: str,
    client_factory: Callable[..., Any] | None = None,
) -> Any:
    if not client_id.strip():
        raise OptionChainDataError("FYERS_CLIENT_ID is missing.")
    if not access_token.strip():
        raise OptionChainDataError("FYERS_ACCESS_TOKEN is missing.")

    if client_factory is None:
        try:
            from fyers_apiv3 import fyersModel
        except ImportError as exc:
            raise OptionChainDataError(
                "fyers_apiv3 is not installed in the HQE environment."
            ) from exc
        client_factory = fyersModel.FyersModel

    possible = {
        "client_id": client_id,
        "token": access_token,
        "is_async": False,
        "log_path": "",
    }

    try:
        signature = inspect.signature(client_factory)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        accepts_kwargs = any(
            parameter.kind
            is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        if not accepts_kwargs:
            possible = {
                key: value
                for key, value in possible.items()
                if key in signature.parameters
            }

    try:
        return client_factory(**possible)
    except Exception as exc:
        raise OptionChainDataError(
            f"FYERS data-only client initialization failed: "
            f"{type(exc).__name__}"
        ) from exc


def fetch_option_chain(
    client: Any,
    *,
    symbol: str,
    strike_count: int,
    expiry_timestamp: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not hasattr(client, "optionchain"):
        raise OptionChainDataError(
            "Installed FYERS client does not expose optionchain()."
        )

    request = {
        "symbol": symbol,
        "strikecount": int(strike_count),
        "timestamp": expiry_timestamp,
    }

    try:
        response = client.optionchain(data=request)
    except Exception as exc:
        raise OptionChainDataError(
            f"FYERS option-chain data request failed: "
            f"{type(exc).__name__}"
        ) from exc

    if not isinstance(response, dict):
        raise OptionChainDataError(
            "FYERS option-chain response was not a JSON object."
        )

    status = _text(response.get("s")).lower()
    if status and status != "ok":
        summary = safe_response_summary(response)
        raise OptionChainDataError(
            "FYERS option-chain response was not successful: "
            f"code={summary['code']} message={summary['message']}"
        )

    return request, response


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(CSV_FIELDS),
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    temporary.replace(path)


def output_paths(
    workspace: Path,
    trading_date: str,
) -> dict[str, Path]:
    folder = (
        workspace
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / trading_date
    )
    return {
        "folder": folder,
        "snapshot_json": (
            folder / "FYERS_NIFTY_OPTION_CHAIN_SNAPSHOT.json"
        ),
        "premium_csv": (
            folder / "FYERS_NIFTY_OPTION_CHAIN_PREMIUM_SNAPSHOT.csv"
        ),
        "status_json": (
            workspace / "HQE_CURRENT_DAY_OPTION_DATA_STATUS.json"
        ),
    }


def build_guard_payload() -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "guard_check_status": "PASS",
        "workflow": "FYERS_OPTION_CHAIN_DATA_ONLY",
        "live_api_call_performed": False,
        "order_api_available_to_module": False,
        "safety_lock": SAFETY_LOCK,
    }


def run_live_data_only(
    *,
    workspace: Path,
    symbol: str,
    trading_date: str,
    strike_count: int,
    expiry_timestamp: str,
    client: Any | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not workspace.exists():
        raise OptionChainDataError(
            f"Workspace does not exist: {workspace}"
        )

    try:
        date.fromisoformat(trading_date)
    except ValueError as exc:
        raise OptionChainDataError(
            "Trading date must use YYYY-MM-DD."
        ) from exc

    environment = env if env is not None else os.environ
    if client is None:
        client = build_fyers_client(
            client_id=environment.get("FYERS_CLIENT_ID", ""),
            access_token=environment.get(
                "FYERS_ACCESS_TOKEN",
                "",
            ),
        )

    request, response = fetch_option_chain(
        client,
        symbol=symbol,
        strike_count=strike_count,
        expiry_timestamp=expiry_timestamp,
    )
    rows = normalize_chain(
        response,
        underlying_symbol=symbol,
        trading_date=trading_date,
        requested_expiry_timestamp=expiry_timestamp,
    )
    readiness = chain_readiness(rows)
    paths = output_paths(workspace, trading_date)

    snapshot = {
        "version": MODULE_VERSION,
        "generated_at_utc": utc_now_text(),
        "trading_date": trading_date,
        "underlying_symbol": symbol,
        "request": request,
        "response_summary": safe_response_summary(response),
        "expiry_data": extract_expiry_data(response),
        "readiness": readiness,
        "paper_only": True,
        "data_only": True,
        "recorded_data_replay_ready": False,
        "historical_premium_candles_ready": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
    }

    write_csv(paths["premium_csv"], rows)
    write_json(paths["snapshot_json"], snapshot)

    status = {
        **snapshot,
        "snapshot_json": str(paths["snapshot_json"]),
        "premium_csv": str(paths["premium_csv"]),
        "live_api_call_performed": True,
        "next_required_step": (
            "FETCH_SELECTED_CE_PE_HISTORICAL_5M_CANDLES"
            if readiness["both_sides_ready"]
            else "REPAIR_OR_REFRESH_OPTION_CHAIN_DATA"
        ),
        "safety_lock": SAFETY_LOCK,
    }
    write_json(paths["status_json"], status)
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "HQE FYERS NIFTY option-chain data-only foundation"
        )
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument(
        "--trading-date",
        default=ist_today_text(),
    )
    parser.add_argument(
        "--strike-count",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--expiry-timestamp",
        default="",
    )
    parser.add_argument(
        "--fetch-live-data-only",
        action="store_true",
    )
    parser.add_argument("--guard-check", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.guard_check:
        print(
            json.dumps(
                build_guard_payload(),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if not args.fetch_live_data_only:
        parser.error(
            "Use --guard-check or explicitly pass "
            "--fetch-live-data-only."
        )
    if args.workspace is None:
        parser.error(
            "--workspace is required with --fetch-live-data-only."
        )

    try:
        payload = run_live_data_only(
            workspace=args.workspace,
            symbol=args.symbol,
            trading_date=args.trading_date,
            strike_count=max(1, args.strike_count),
            expiry_timestamp=args.expiry_timestamp,
        )
    except OptionChainDataError as exc:
        failure = {
            "version": MODULE_VERSION,
            "status": "FAILED_SAFE",
            "error": str(exc),
            "live_api_call_performed": True,
            "paper_only": True,
            "data_only": True,
            "real_orders_allowed": False,
            "broker_execution_allowed": False,
            "auto_trading_allowed": False,
            "option_selling_allowed": False,
            "safety_lock": SAFETY_LOCK,
        }
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2

    print(json.dumps(payload, indent=2, sort_keys=True))
    return (
        0
        if payload["readiness"]["both_sides_ready"]
        else 3
    )


if __name__ == "__main__":
    raise SystemExit(main())
