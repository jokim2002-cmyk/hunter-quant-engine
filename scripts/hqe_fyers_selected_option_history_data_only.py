from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from hqe_fyers_option_chain_data_only import (
    SAFETY_LOCK,
    build_fyers_client,
)

MODULE_VERSION = "HQE_FYERS_SELECTED_OPTION_HISTORY_DATA_ONLY_V1"
IST = ZoneInfo("Asia/Kolkata")

OUTPUT_FIELDS = (
    "timestamp",
    "timestamp_utc",
    "trading_date",
    "symbol",
    "option_type",
    "signal_side",
    "strike_price",
    "expiry_timestamp",
    "dte",
    "open",
    "high",
    "low",
    "close",
    "ltp",
    "volume",
    "source",
)


class SelectedOptionHistoryError(RuntimeError):
    pass


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    numeric = _number(value)
    return None if numeric is None else int(numeric)


def _side(row: dict[str, Any]) -> str:
    side = _text(row.get("signal_side")).upper()
    if side in {"CE_BUY", "PE_BUY"}:
        return side

    option_type = _text(row.get("option_type")).upper()
    if option_type in {"CE", "CALL"}:
        return "CE_BUY"
    if option_type in {"PE", "PUT"}:
        return "PE_BUY"

    symbol = _text(row.get("symbol")).upper()
    if symbol.endswith("CE"):
        return "CE_BUY"
    if symbol.endswith("PE"):
        return "PE_BUY"
    return "NO_TRADE"


def _option_type(row: dict[str, Any]) -> str:
    return "CE" if _side(row) == "CE_BUY" else "PE"


def read_chain_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SelectedOptionHistoryError(
            f"Option-chain snapshot CSV is missing: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SelectedOptionHistoryError(
            "Option-chain snapshot CSV could not be read."
        ) from exc


def _eligible(
    row: dict[str, Any],
    *,
    min_dte: int,
    min_ltp: float,
    max_ltp: float,
) -> bool:
    side = _side(row)
    symbol = _text(row.get("symbol"))
    strike = _number(row.get("strike_price"))
    ltp = _number(row.get("ltp"))
    dte = _integer(row.get("dte"))

    return bool(
        side in {"CE_BUY", "PE_BUY"}
        and symbol
        and strike is not None
        and ltp is not None
        and dte is not None
        and dte >= min_dte
        and min_ltp <= ltp <= max_ltp
    )


def select_ce_pe_pair(
    rows: list[dict[str, Any]],
    *,
    min_dte: int = 1,
    min_ltp: float = 20.0,
    max_ltp: float = 200.0,
) -> dict[str, Any]:
    eligible = [
        row
        for row in rows
        if _eligible(
            row,
            min_dte=min_dte,
            min_ltp=min_ltp,
            max_ltp=max_ltp,
        )
    ]

    by_expiry_and_strike: dict[
        tuple[int, float],
        dict[str, list[dict[str, Any]]],
    ] = defaultdict(lambda: {"CE_BUY": [], "PE_BUY": []})

    for row in eligible:
        key = (
            int(_integer(row.get("dte")) or 0),
            float(_number(row.get("strike_price")) or 0.0),
        )
        by_expiry_and_strike[key][_side(row)].append(row)

    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for (dte, strike), sides in by_expiry_and_strike.items():
        if not sides["CE_BUY"] or not sides["PE_BUY"]:
            continue

        ce = max(
            sides["CE_BUY"],
            key=lambda row: (
                _number(row.get("volume")) or 0.0,
                _number(row.get("oi")) or 0.0,
            ),
        )
        pe = max(
            sides["PE_BUY"],
            key=lambda row: (
                _number(row.get("volume")) or 0.0,
                _number(row.get("oi")) or 0.0,
            ),
        )

        ce_ltp = float(_number(ce.get("ltp")) or 0.0)
        pe_ltp = float(_number(pe.get("ltp")) or 0.0)
        premium_gap = abs(ce_ltp - pe_ltp)
        average_premium = (ce_ltp + pe_ltp) / 2.0

        selection = {
            "selection_method": (
                "NEAREST_EXPIRY_SAME_STRIKE_BALANCED_PREMIUM"
            ),
            "dte": dte,
            "strike_price": strike,
            "ce": dict(ce),
            "pe": dict(pe),
            "ce_ltp": ce_ltp,
            "pe_ltp": pe_ltp,
            "premium_gap": premium_gap,
            "average_premium": average_premium,
        }

        score = (
            dte,
            premium_gap,
            abs(average_premium - 100.0),
            strike,
        )
        candidates.append((score, selection))

    if not candidates:
        ce_count = sum(1 for row in eligible if _side(row) == "CE_BUY")
        pe_count = sum(1 for row in eligible if _side(row) == "PE_BUY")
        raise SelectedOptionHistoryError(
            "No same-expiry, same-strike CE/PE pair passed the "
            f"DTE and premium guards. Eligible CE={ce_count}, PE={pe_count}."
        )

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def history_request(
    *,
    symbol: str,
    trading_date: str,
    resolution: str = "5",
) -> dict[str, str]:
    try:
        date.fromisoformat(trading_date)
    except ValueError as exc:
        raise SelectedOptionHistoryError(
            "Trading date must use YYYY-MM-DD."
        ) from exc

    return {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": "1",
        "range_from": trading_date,
        "range_to": trading_date,
        "cont_flag": "1",
    }


def fetch_history(
    client: Any,
    *,
    symbol: str,
    trading_date: str,
    resolution: str = "5",
) -> tuple[dict[str, str], dict[str, Any]]:
    if not hasattr(client, "history"):
        raise SelectedOptionHistoryError(
            "Installed FYERS client does not expose history()."
        )

    request = history_request(
        symbol=symbol,
        trading_date=trading_date,
        resolution=resolution,
    )

    try:
        response = client.history(data=request)
    except Exception as exc:
        raise SelectedOptionHistoryError(
            f"FYERS history request failed for {symbol}: "
            f"{type(exc).__name__}"
        ) from exc

    if not isinstance(response, dict):
        raise SelectedOptionHistoryError(
            f"FYERS history response was not JSON for {symbol}."
        )

    status = _text(response.get("s")).lower()
    candles = response.get("candles")
    if status and status != "ok":
        raise SelectedOptionHistoryError(
            "FYERS history response failed for "
            f"{symbol}: code={response.get('code')} "
            f"message={_text(response.get('message') or response.get('msg'))[:200]}"
        )
    if not isinstance(candles, list) or not candles:
        raise SelectedOptionHistoryError(
            f"FYERS returned no historical candles for {symbol} "
            f"on {trading_date}."
        )

    return request, response


def normalize_candles(
    response: dict[str, Any],
    *,
    selection_row: dict[str, Any],
    trading_date: str,
) -> list[dict[str, Any]]:
    symbol = _text(selection_row.get("symbol"))
    side = _side(selection_row)
    option_type = _option_type(selection_row)
    strike = _number(selection_row.get("strike_price"))
    expiry = _text(selection_row.get("expiry_timestamp"))
    dte = _integer(selection_row.get("dte"))

    normalized: list[dict[str, Any]] = []
    for candle in response.get("candles", []):
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue

        epoch = _integer(candle[0])
        opened = _number(candle[1])
        high = _number(candle[2])
        low = _number(candle[3])
        close = _number(candle[4])
        volume = _number(candle[5])

        if (
            epoch is None
            or opened is None
            or high is None
            or low is None
            or close is None
        ):
            continue

        utc_dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        ist_dt = utc_dt.astimezone(IST)

        if ist_dt.date().isoformat() != trading_date:
            continue

        normalized.append(
            {
                "timestamp": ist_dt.replace(tzinfo=None).isoformat(
                    sep=" ",
                    timespec="seconds",
                ),
                "timestamp_utc": utc_dt.isoformat(timespec="seconds"),
                "trading_date": trading_date,
                "symbol": symbol,
                "option_type": option_type,
                "signal_side": side,
                "strike_price": strike,
                "expiry_timestamp": expiry,
                "dte": dte,
                "open": opened,
                "high": high,
                "low": low,
                "close": close,
                "ltp": close,
                "volume": volume,
                "source": "FYERS_HISTORY_5M_DATA_ONLY",
            }
        )

    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in normalized:
        deduped[(row["symbol"], row["timestamp"])] = row

    return sorted(
        deduped.values(),
        key=lambda row: (row["timestamp"], row["signal_side"]),
    )


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


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
            fieldnames=list(OUTPUT_FIELDS),
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
        / "SELECTED_OPTION_HISTORY_5M"
    )
    return {
        "folder": folder,
        "ce_csv": folder / "SELECTED_CE_HISTORY_5M.csv",
        "pe_csv": folder / "SELECTED_PE_HISTORY_5M.csv",
        "combined_csv": (
            folder / "SELECTED_CE_PE_HISTORY_5M_COMBINED.csv"
        ),
        "status_json": (
            workspace
            / "HQE_CURRENT_DAY_SELECTED_OPTION_HISTORY_STATUS.json"
        ),
    }


def default_chain_csv(
    workspace: Path,
    trading_date: str,
) -> Path:
    return (
        workspace
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / trading_date
        / "FYERS_NIFTY_OPTION_CHAIN_PREMIUM_SNAPSHOT.csv"
    )


def run_live_data_only(
    *,
    workspace: Path,
    trading_date: str,
    option_chain_csv: Path | None = None,
    client: Any | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not workspace.exists():
        raise SelectedOptionHistoryError(
            f"Workspace does not exist: {workspace}"
        )

    chain_csv = option_chain_csv or default_chain_csv(
        workspace,
        trading_date,
    )
    chain_rows = read_chain_csv(chain_csv)
    selection = select_ce_pe_pair(chain_rows)

    if client is None:
        environment = env if env is not None else __import__("os").environ
        client = build_fyers_client(
            client_id=environment.get("FYERS_CLIENT_ID", ""),
            access_token=environment.get("FYERS_ACCESS_TOKEN", ""),
        )

    ce_request, ce_response = fetch_history(
        client,
        symbol=_text(selection["ce"].get("symbol")),
        trading_date=trading_date,
    )
    pe_request, pe_response = fetch_history(
        client,
        symbol=_text(selection["pe"].get("symbol")),
        trading_date=trading_date,
    )

    ce_rows = normalize_candles(
        ce_response,
        selection_row=selection["ce"],
        trading_date=trading_date,
    )
    pe_rows = normalize_candles(
        pe_response,
        selection_row=selection["pe"],
        trading_date=trading_date,
    )

    if not ce_rows or not pe_rows:
        raise SelectedOptionHistoryError(
            "Both genuine CE and PE historical 5-minute candle sets "
            "are required. No rows were fabricated."
        )

    combined = sorted(
        [*ce_rows, *pe_rows],
        key=lambda row: (row["timestamp"], row["signal_side"]),
    )
    paths = output_paths(workspace, trading_date)

    _atomic_csv(paths["ce_csv"], ce_rows)
    _atomic_csv(paths["pe_csv"], pe_rows)
    _atomic_csv(paths["combined_csv"], combined)

    payload = {
        "version": MODULE_VERSION,
        "status": "SELECTED_CE_PE_HISTORY_5M_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "trading_date": trading_date,
        "option_chain_csv": str(chain_csv),
        "selection": {
            "method": selection["selection_method"],
            "strike_price": selection["strike_price"],
            "dte": selection["dte"],
            "ce_symbol": _text(selection["ce"].get("symbol")),
            "pe_symbol": _text(selection["pe"].get("symbol")),
            "ce_snapshot_ltp": selection["ce_ltp"],
            "pe_snapshot_ltp": selection["pe_ltp"],
            "premium_gap": selection["premium_gap"],
        },
        "requests": {
            "ce": ce_request,
            "pe": pe_request,
        },
        "rows": {
            "ce": len(ce_rows),
            "pe": len(pe_rows),
            "combined": len(combined),
        },
        "outputs": {
            "ce_csv": str(paths["ce_csv"]),
            "pe_csv": str(paths["pe_csv"]),
            "combined_csv": str(paths["combined_csv"]),
        },
        "genuine_fyers_history": True,
        "recorded_data_replay_ready": False,
        "supervisor_wired": False,
        "report_generated": False,
        "paper_only": True,
        "data_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "safety_lock": SAFETY_LOCK,
        "next_required_step": (
            "WIRE_SELECTED_HISTORY_TO_TRUTHFUL_RECORDED_DATA_REPLAY"
        ),
    }
    _atomic_json(paths["status_json"], payload)
    return payload


def guard_payload() -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "guard_check_status": "PASS",
        "workflow": "SELECTED_CE_PE_HISTORY_5M_DATA_ONLY",
        "live_api_call_performed": False,
        "order_api_available_to_module": False,
        "paper_only": True,
        "data_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "safety_lock": SAFETY_LOCK,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch selected NIFTY CE and PE historical 5-minute "
            "candles using FYERS data-only history API."
        )
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--trading-date", default="")
    parser.add_argument("--option-chain-csv", type=Path)
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
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0

    if not args.fetch_live_data_only:
        parser.error(
            "Use --guard-check or explicitly pass "
            "--fetch-live-data-only."
        )
    if args.workspace is None:
        parser.error("--workspace is required.")
    if not args.trading_date:
        parser.error("--trading-date is required.")

    try:
        payload = run_live_data_only(
            workspace=args.workspace,
            trading_date=args.trading_date,
            option_chain_csv=args.option_chain_csv,
        )
    except SelectedOptionHistoryError as exc:
        print(
            json.dumps(
                {
                    "version": MODULE_VERSION,
                    "status": "FAILED_SAFE",
                    "error": str(exc),
                    "paper_only": True,
                    "data_only": True,
                    "real_orders_allowed": False,
                    "broker_execution_allowed": False,
                    "auto_trading_allowed": False,
                    "option_selling_allowed": False,
                    "safety_lock": SAFETY_LOCK,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
