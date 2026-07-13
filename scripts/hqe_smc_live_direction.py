from __future__ import annotations

import csv
import inspect
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.paper_trading import recorded_data_strategy_decision_audit as smc_audit


DECISION_TO_SIDE = {
    "LONG": "CE_BUY",
    "SHORT": "PE_BUY",
    "NEUTRAL": "NO_TRADE",
}


def map_decision(decision: str) -> str:
    return DECISION_TO_SIDE.get(str(decision).upper(), "NO_TRADE")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, UnicodeError, csv.Error):
        return []


def _first(row: dict[str, str], names: tuple[str, ...]) -> str:
    lowered = {
        str(key).strip().lower(): str(value).strip()
        for key, value in row.items()
        if key is not None and value is not None
    }
    for name in names:
        value = lowered.get(name.lower(), "")
        if value:
            return value
    return ""


def _number(row: dict[str, str], names: tuple[str, ...]) -> float | None:
    raw = _first(row, names)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _timestamp(row: dict[str, str]) -> str:
    return _first(
        row,
        (
            "timestamp",
            "datetime",
            "date_time",
            "signal_time",
            "entry_time",
            "time",
            "date",
        ),
    )


def _index_events(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in rows:
        opened = _number(row, ("open", "o"))
        high = _number(row, ("high", "h"))
        low = _number(row, ("low", "l"))
        close = _number(row, ("close", "c", "ltp"))
        if None in (opened, high, low, close):
            continue
        events.append(
            {
                "timestamp": _timestamp(row),
                "open": opened,
                "high": high,
                "low": low,
                "close": close,
                "volume": _number(row, ("volume", "vol", "v")),
            }
        )
    events.sort(key=lambda item: str(item.get("timestamp", "")))
    return events


def _option_side(row: dict[str, str]) -> str:
    explicit = _first(
        row,
        (
            "signal_side",
            "side",
            "option_type",
            "right",
            "instrument_type",
        ),
    ).upper()
    if explicit in {"CE", "CE_BUY", "CALL", "CALL_BUY"}:
        return "CE_BUY"
    if explicit in {"PE", "PE_BUY", "PUT", "PUT_BUY"}:
        return "PE_BUY"

    symbol = _first(
        row,
        (
            "option_symbol",
            "symbol",
            "tradingsymbol",
            "instrument",
            "ticker",
        ),
    ).upper()
    if symbol.endswith("CE"):
        return "CE_BUY"
    if symbol.endswith("PE"):
        return "PE_BUY"
    return "NO_TRADE"


def _option_price(row: dict[str, str]) -> float | None:
    return _number(
        row,
        (
            "last_traded_price",
            "ltp",
            "price",
            "premium",
            "entry_price",
            "close",
        ),
    )


def _option_dte(row: dict[str, str]) -> int | None:
    raw = _number(row, ("dte", "days_to_expiry"))
    return None if raw is None else int(raw)


def _run_gate(
    events: list[dict[str, Any]],
) -> tuple[str, str, float | None]:
    current = events[-1]
    history = events[:-1]
    previous_close = history[-1]["close"] if history else None

    function = smc_audit._decision_for_smc_parameter_gate
    signature = inspect.signature(function)
    kwargs: dict[str, Any] = {}

    for name, parameter in signature.parameters.items():
        if name == "previous_close":
            kwargs[name] = previous_close
        elif name == "close":
            kwargs[name] = current["close"]
        elif name in {"event", "current_event"}:
            kwargs[name] = current
        elif name in {"previous_events", "history", "valid_history"}:
            kwargs[name] = history
        elif name in {
            "total_sandbox_events",
            "total_events",
            "event_count",
        }:
            kwargs[name] = len(events)
        elif name == "threshold_points":
            kwargs[name] = 0.0
        elif parameter.default is inspect.Parameter.empty:
            return (
                "NEUTRAL",
                f"smc_live_unsupported_parameter={name}",
                None,
            )

    try:
        decision, reason, close_change = function(**kwargs)
    except Exception as exc:
        return (
            "NEUTRAL",
            f"smc_live_gate_error={type(exc).__name__}:{exc}",
            None,
        )

    return str(decision).upper(), str(reason), close_change


def _select_option(
    rows: list[dict[str, str]],
    side: str,
    candidate: dict[str, Any],
) -> tuple[float | None, int | None, str]:
    min_price = float(candidate["min_last_traded_price"])
    max_price = float(candidate["max_last_traded_price"])
    min_dte = int(candidate["min_dte"])

    matching = [row for row in rows if _option_side(row) == side]
    matching.sort(key=_timestamp)

    if not matching:
        return None, None, f"{side}_DATA_NOT_AVAILABLE"

    for row in reversed(matching):
        price = _option_price(row)
        dte = _option_dte(row)
        if price is None or dte is None:
            continue
        if dte < min_dte:
            continue
        if not (min_price <= price <= max_price):
            continue
        return round(price, 2), dte, "MATCHING_OPTION_READY"

    return None, None, f"{side}_FAILED_DTE_OR_PREMIUM_GUARD"


def evaluate_from_csv(
    index_csv: Path,
    premium_csv: Path,
    candidate: dict[str, Any],
    er20: float | None,
) -> dict[str, Any]:
    index_rows = _read_csv(index_csv)
    premium_rows = _read_csv(premium_csv)
    events = _index_events(index_rows)

    available_sides = {
        _option_side(row)
        for row in premium_rows
        if _option_side(row) in {"CE_BUY", "PE_BUY"}
    }

    # Old tests and historical packs contain PE-only premium data.
    # Keep that path untouched. Bidirectional SMC activates only when
    # both CE and PE data are genuinely available in the current cycle.
    if available_sides != {"CE_BUY", "PE_BUY"}:
        return {
            "fallback_to_legacy": True,
            "decision": "LEGACY_COMPATIBILITY",
            "side": "PE_BUY",
            "signal_generated": False,
            "reason": (
                "BIDIRECTIONAL_PREMIUM_DATA_INCOMPLETE;"
                f"available={sorted(available_sides)}"
            ),
            "entry": None,
            "stop_loss": None,
            "target": None,
            "ltp": None,
            "dte": None,
        }

    minimum_history = int(
        getattr(smc_audit, "SMC_MIN_HISTORY_BARS", 20)
    )
    if len(events) < minimum_history + 1:
        return {
            "fallback_to_legacy": True,
            "decision": "LEGACY_COMPATIBILITY",
            "side": "PE_BUY",
            "signal_generated": False,
            "reason": (
                "SMC_HISTORY_NOT_ENOUGH_FOR_LIVE_GATE;"
                f"required={minimum_history + 1};actual={len(events)}"
            ),
            "entry": None,
            "stop_loss": None,
            "target": None,
            "ltp": None,
            "dte": None,
        }

    decision, gate_reason, close_change = _run_gate(events)
    side = map_decision(decision)

    if side == "NO_TRADE":
        return {
            "fallback_to_legacy": False,
            "decision": decision,
            "side": side,
            "signal_generated": False,
            "reason": (
                f"SMC_DECISION={decision};OPTION_SIDE=NO_TRADE;"
                f"{gate_reason}"
            ),
            "entry": None,
            "stop_loss": None,
            "target": None,
            "ltp": None,
            "dte": None,
            "close_change": close_change,
        }

    if er20 is None:
        return {
            "fallback_to_legacy": False,
            "decision": decision,
            "side": side,
            "signal_generated": False,
            "reason": (
                f"SMC_DECISION={decision};OPTION_SIDE={side};"
                "ER20_NOT_AVAILABLE"
            ),
            "entry": None,
            "stop_loss": None,
            "target": None,
            "ltp": None,
            "dte": None,
            "close_change": close_change,
        }

    if er20 < 0.30:
        return {
            "fallback_to_legacy": False,
            "decision": decision,
            "side": side,
            "signal_generated": False,
            "reason": (
                f"SMC_DECISION={decision};OPTION_SIDE={side};"
                f"ER20_REJECT_LT_0.30({er20:.4f})"
            ),
            "entry": None,
            "stop_loss": None,
            "target": None,
            "ltp": None,
            "dte": None,
            "close_change": close_change,
        }

    entry, dte, option_reason = _select_option(
        premium_rows,
        side,
        candidate,
    )
    if entry is None:
        return {
            "fallback_to_legacy": False,
            "decision": decision,
            "side": side,
            "signal_generated": False,
            "reason": (
                f"SMC_DECISION={decision};OPTION_SIDE={side};"
                f"{gate_reason};{option_reason}"
            ),
            "entry": None,
            "stop_loss": None,
            "target": None,
            "ltp": None,
            "dte": None,
            "close_change": close_change,
        }

    stop_loss = round(
        entry * (1.0 - float(candidate["stop_loss_percent"])),
        2,
    )
    target = round(
        entry * (1.0 + float(candidate["target_percent"])),
        2,
    )

    return {
        "fallback_to_legacy": False,
        "decision": decision,
        "side": side,
        "signal_generated": True,
        "reason": (
            f"SMC_DECISION={decision};OPTION_SIDE={side};"
            f"{gate_reason};{option_reason};ER20_OK({er20:.4f})"
        ),
        "entry": entry,
        "stop_loss": stop_loss,
        "target": target,
        "ltp": entry,
        "dte": dte,
        "close_change": close_change,
    }
