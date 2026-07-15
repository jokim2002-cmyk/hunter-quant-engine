"""
Module 131: Forward Intraday Paper Supervisor

Read-only, paper-only supervisor for locked HQE forward validation candidate.

Safety contract:
- Paper/simulation only
- No broker execution
- No real orders
- No real money approval
- No auto trading enablement
- Option-buy only, PE paper plan only
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import sys as _hqe_sys
_HQE_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_HQE_SCRIPT_DIR) not in _hqe_sys.path:
    _hqe_sys.path.insert(0, str(_HQE_SCRIPT_DIR))
from hqe_smc_live_direction import evaluate_from_csv



MODULE_ID = 131
MODULE_NAME = "Forward Intraday Paper Supervisor"

PAPER_ONLY = True
REAL_MONEY_ALLOWED = False
BROKER_EXECUTION_ALLOWED = False
REAL_ORDERS_ALLOWED = False
AUTO_TRADING_ALLOWED = False
OPTION_SELLING_ALLOWED = False

LOCKED_CANDIDATE = {
    "filter": "ER20_GE_030",
    "direction": "PE_ONLY",
    "min_dte": 1,
    "min_last_traded_price": 20.0,
    "max_last_traded_price": 200.0,
    "stop_loss_percent": 0.40,
    "target_percent": 1.20,
    "name": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
}

ACTIVE_SMC_CANDIDATE = {
    "filter": "SMC_PARAMETER_ALIGNED_AND_ER20_GE_030",
    "direction": "SMC_BIDIRECTIONAL",
    "min_dte": 1,
    "min_last_traded_price": 20.0,
    "max_last_traded_price": 200.0,
    "stop_loss_percent": 0.40,
    "target_percent": 1.20,
    "name": (
        "SMC_BIDIRECTIONAL_ER20_GE_030_LONG_CE_SHORT_PE_"
        "DTE_GE_1_LTP_20_200_SL040_TGT120"
    ),
}


MARKET_START = (9, 15)
MARKET_END = (15, 30)
DEFAULT_CYCLE_SECONDS = 300


@dataclass(frozen=True)
class SupervisorPaths:
    index_csv: Path
    premium_csv: Path
    out_dir: Path
    state_json: Path
    ledger_csv: Path


@dataclass(frozen=True)
class Candle:
    dt: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    last_traded_price: float | None = None
    dte: int | None = None
    symbol: str = ""
    signal_side: str = ""


@dataclass(frozen=True)
class SignalDecision:
    signal_generated: bool
    pe_reason: str
    entry: float | None
    stop_loss: float | None
    target: float | None
    er20: float | None
    dte: int | None
    ltp: float | None


def assert_safety_contract() -> None:
    if not PAPER_ONLY:
        raise RuntimeError("SAFETY_FAIL: PAPER_ONLY must stay True.")
    blocked = {
        "REAL_MONEY_ALLOWED": REAL_MONEY_ALLOWED,
        "BROKER_EXECUTION_ALLOWED": BROKER_EXECUTION_ALLOWED,
        "REAL_ORDERS_ALLOWED": REAL_ORDERS_ALLOWED,
        "AUTO_TRADING_ALLOWED": AUTO_TRADING_ALLOWED,
        "OPTION_SELLING_ALLOWED": OPTION_SELLING_ALLOWED,
    }
    enabled = [name for name, value in blocked.items() if value]
    if enabled:
        raise RuntimeError("SAFETY_FAIL: blocked capability enabled: " + ",".join(enabled))


def parse_dt(value: str) -> datetime:
    text = str(value).strip()
    if not text:
        raise ValueError("empty datetime")
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unsupported datetime format: {value!r}")


def to_float(row: dict[str, str], *names: str, default: float | None = None) -> float:
    for name in names:
        raw = row.get(name)
        if raw is not None and str(raw).strip() != "":
            return float(raw)
    if default is not None:
        return default
    raise KeyError("missing numeric field: " + "/".join(names))


def to_int(row: dict[str, str], *names: str, default: int | None = None) -> int:
    for name in names:
        raw = row.get(name)
        if raw is not None and str(raw).strip() != "":
            return int(float(raw))
    if default is not None:
        return default
    raise KeyError("missing integer field: " + "/".join(names))


def read_candles(path: Path, *, premium: bool) -> list[Candle]:
    if not path.exists():
        return []
    rows: list[Candle] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        reader.fieldnames = [str(name).strip() for name in reader.fieldnames]
        for raw_row in reader:
            row = {str(k).strip(): str(v).strip() for k, v in raw_row.items() if k is not None}
            dt = parse_dt(row.get("datetime") or row.get("timestamp") or row.get("time") or "")
            close_value = to_float(row, "close", "last_traded_price", "ltp")
            last_traded_price = (
                to_float(row, "last_traded_price", "ltp", "close") if premium else None
            )
            dte = to_int(row, "dte", "days_to_expiry", default=1) if premium else None

            raw_side = (
                row.get("signal_side")
                or row.get("option_type")
                or ""
            ).strip().upper()

            if raw_side == "CE":
                raw_side = "CE_BUY"
            elif raw_side == "PE":
                raw_side = "PE_BUY"

            rows.append(
                Candle(
                    dt=dt,
                    open=to_float(row, "open", default=close_value),
                    high=to_float(row, "high", default=close_value),
                    low=to_float(row, "low", default=close_value),
                    close=close_value,
                    volume=to_float(row, "volume", default=0.0),
                    last_traded_price=last_traded_price,
                    dte=dte,
                    symbol=(row.get("symbol") or row.get("tradingsymbol") or "").strip(),
                    signal_side=raw_side if premium else "",
                )
            )
    return sorted(rows, key=lambda candle: candle.dt)


def is_market_time(now: datetime) -> bool:
    start_hour, start_minute = MARKET_START
    end_hour, end_minute = MARKET_END
    return (now.hour, now.minute) >= (start_hour, start_minute) and (
        now.hour,
        now.minute,
    ) <= (end_hour, end_minute)


def efficiency_ratio(closes: list[float], lookback: int = 20) -> float | None:
    if len(closes) < lookback + 1:
        return None
    window = closes[-(lookback + 1):]
    direction = abs(window[-1] - window[0])
    volatility = sum(abs(window[index] - window[index - 1]) for index in range(1, len(window)))
    if volatility == 0:
        return 0.0
    return direction / volatility


def data_ready(index_candles: list[Candle], premium_candles: list[Candle], now: datetime) -> tuple[bool, str]:
    if not is_market_time(now):
        return False, "MARKET_TIME_NOT_ACTIVE_0915_TO_1530"
    if len(index_candles) < 21:
        return False, "INDEX_DATA_NOT_READY_MIN_21_CANDLES_REQUIRED"
    if not premium_candles:
        return False, "PREMIUM_DATA_NOT_READY"
    latest_index = index_candles[-1]
    latest_premium = premium_candles[-1]
    if latest_index.dt.date() != now.date():
        return False, "INDEX_DATA_NOT_FRESH_FOR_TODAY"
    if latest_premium.dt.date() != now.date():
        return False, "PREMIUM_DATA_NOT_FRESH_FOR_TODAY"
    age_minutes = abs((now - latest_index.dt).total_seconds()) / 60.0
    if age_minutes > 10:
        return False, f"INDEX_DATA_STALE_{age_minutes:.1f}_MINUTES"
    return True, "DATA_READY"


def build_locked_pe_signal(index_candles: list[Candle], premium_candles: list[Candle]) -> SignalDecision:
    closes = [candle.close for candle in index_candles]
    er20 = efficiency_ratio(closes, 20)
    latest_index = index_candles[-1]
    reference_index = index_candles[-21]
    latest_premium = premium_candles[-1]
    ltp = latest_premium.last_traded_price if latest_premium.last_traded_price is not None else latest_premium.close
    dte = latest_premium.dte if latest_premium.dte is not None else 0

    reasons: list[str] = []
    if er20 is None:
        reasons.append("ER20_NOT_AVAILABLE")
    elif er20 < 0.30:
        reasons.append(f"ER20_BELOW_030({er20:.4f})")
    else:
        reasons.append(f"ER20_OK({er20:.4f})")

    if latest_index.close >= reference_index.close:
        reasons.append("PE_REJECT_INDEX_NOT_FALLING")
    else:
        reasons.append("PE_OK_INDEX_FALLING")

    if dte < int(LOCKED_CANDIDATE["min_dte"]):
        reasons.append(f"DTE_REJECT_LT_1({dte})")
    else:
        reasons.append(f"DTE_OK({dte})")

    min_ltp = float(LOCKED_CANDIDATE["min_last_traded_price"])
    max_ltp = float(LOCKED_CANDIDATE["max_last_traded_price"])
    if not (min_ltp <= ltp <= max_ltp):
        reasons.append(f"LTP_REJECT_OUT_OF_RANGE({ltp:.2f})")
    else:
        reasons.append(f"LTP_OK({ltp:.2f})")

    signal_generated = (
        er20 is not None
        and er20 >= 0.30
        and latest_index.close < reference_index.close
        and dte >= int(LOCKED_CANDIDATE["min_dte"])
        and min_ltp <= ltp <= max_ltp
    )

    if signal_generated:
        entry = round(ltp, 2)
        stop_loss = round(entry * (1.0 - float(LOCKED_CANDIDATE["stop_loss_percent"])), 2)
        target = round(entry * (1.0 + float(LOCKED_CANDIDATE["target_percent"])), 2)
    else:
        entry = None
        stop_loss = None
        target = None

    return SignalDecision(
        signal_generated=signal_generated,
        pe_reason="; ".join(reasons),
        entry=entry,
        stop_loss=stop_loss,
        target=target,
        er20=er20,
        dte=dte,
        ltp=ltp,
    )


def evaluate_active_smc_candidate(
    index_csv,
    premium_csv,
    *legacy_args,
    **legacy_kwargs,
):
    legacy = build_locked_pe_signal(*legacy_args, **legacy_kwargs)
    directional = evaluate_from_csv(
        Path(index_csv),
        Path(premium_csv),
        ACTIVE_SMC_CANDIDATE,
        legacy.er20,
    )
    if directional["fallback_to_legacy"]:
        return legacy
    return SignalDecision(
        signal_generated=directional["signal_generated"],
        pe_reason=directional["reason"],
        entry=directional["entry"],
        stop_loss=directional["stop_loss"],
        target=directional["target"],
        er20=legacy.er20,
        dte=(
            directional["dte"]
            if directional["dte"] is not None
            else legacy.dte
        ),
        ltp=(
            directional["ltp"]
            if directional["ltp"] is not None
            else legacy.ltp
        ),
    )



def load_position_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "FLAT", "paper_only": True, "module": MODULE_ID}
    try:
        with path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        if not isinstance(state, dict):
            return {"status": "FLAT", "paper_only": True, "module": MODULE_ID}
        return state
    except json.JSONDecodeError:
        return {"status": "FLAT", "paper_only": True, "module": MODULE_ID, "state_warning": "CORRUPT_STATE_RESET"}


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def append_csv(path: Path, row: dict[str, Any], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = list(fieldnames)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def select_position_premium_candle(
    premium_candles: list[Candle],
    state: dict[str, Any],
) -> Candle | None:
    side = str(state.get("side", "")).strip().upper()
    symbol = str(state.get("option_symbol", "")).strip()

    exact = [
        candle
        for candle in premium_candles
        if candle.signal_side == side
        and (not symbol or candle.symbol == symbol)
    ]
    if exact:
        return exact[-1]

    same_side = [
        candle
        for candle in premium_candles
        if candle.signal_side == side
    ]
    if same_side:
        return same_side[-1]

    # Legacy single-premium CSV files do not contain side/symbol metadata.
    # Use their latest candle only when the complete stream is unlabelled.
    if premium_candles and not any(
        candle.signal_side for candle in premium_candles
    ):
        return premium_candles[-1]

    return None


def evaluate_open_position(
    state: dict[str, Any],
    latest_premium: Candle,
    now: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    entry = float(state["entry"])
    stop_loss = float(state["stop_loss"])
    target = float(state["target"])
    quantity = int(state.get("quantity", 1))
    side = str(state.get("side", ""))
    option_symbol = str(state.get("option_symbol", ""))

    exit_price: float | None = None
    exit_reason = "HOLD_OPEN_PAPER_POSITION"

    if latest_premium.high >= target:
        exit_price = target
        exit_reason = "TARGET_HIT_PAPER_ONLY"
    elif latest_premium.low <= stop_loss:
        exit_price = stop_loss
        exit_reason = "STOP_LOSS_HIT_PAPER_ONLY"
    elif (now.hour, now.minute) >= (15, 25):
        exit_price = latest_premium.last_traded_price or latest_premium.close
        exit_reason = "EOD_EXIT_PAPER_ONLY"

    base_event = {
        "side": side,
        "option_symbol": option_symbol,
        "entry": entry,
        "stop_loss": stop_loss,
        "target": target,
    }

    if exit_price is None:
        event = {
            **base_event,
            "event": "POSITION_HELD",
            "exit_reason": exit_reason,
            "paper_pnl": 0.0,
            "status": "OPEN",
        }
        return state, event

    pnl = round((float(exit_price) - entry) * quantity, 2)

    closed_state = {
        "status": "FLAT",
        "paper_only": True,
        "module": MODULE_ID,
        "side": side,
        "option_symbol": option_symbol,
        "last_entry": entry,
        "last_stop_loss": stop_loss,
        "last_target": target,
        "last_exit_time": now.isoformat(timespec="seconds"),
        "last_exit_price": round(float(exit_price), 2),
        "last_exit_reason": exit_reason,
        "last_paper_pnl": pnl,
        "last_closed_side": side,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
    }

    event = {
        **base_event,
        "event": "POSITION_CLOSED",
        "exit_reason": exit_reason,
        "exit_price": round(float(exit_price), 2),
        "paper_pnl": pnl,
        "status": "FLAT",
    }
    return closed_state, event


def evaluator_status_text(ledger_csv: Path) -> str:
    if not ledger_csv.exists():
        return "HOLD_MORE_DATA_REQUIRED_LEDGER_NOT_FOUND"
    with ledger_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    completed_trades = len([row for row in rows if str(row.get("event", "")).upper() == "POSITION_CLOSED"])
    if completed_trades < 30:
        return f"HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_{completed_trades}_OF_30"
    return f"FORWARD_MIN_TRADE_COUNT_REACHED_{completed_trades}_OF_30_PAPER_ONLY_REVIEW_REQUIRED"


def write_report(
    report_path: Path,
    *,
    now: datetime,
    ready: bool,
    readiness_reason: str,
    signal: SignalDecision | None,
    event: dict[str, Any],
    state: dict[str, Any],
    ledger_status: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    signal_text = "NO_SIGNAL"
    if signal and signal.signal_generated:
        signal_side = (
            "CE_BUY"
            if "OPTION_SIDE=CE_BUY" in signal.pe_reason
            else "PE_BUY"
        )
        signal_text = f"SIGNAL_GENERATED_{signal_side}_PAPER_ONLY"
    lines = [
        f"# HQE Module {MODULE_ID} - {MODULE_NAME}",
        "",
        "## Safety",
        "- Paper/simulation only: YES",
        "- Broker execution: NO",
        "- Real orders: NO",
        "- Real money approval: NO",
        "- Auto trading: NO",
        "- Option selling: NO",
        "- Profitability claim: NO",
        "",
        "## Locked Candidate",
        f"- {LOCKED_CANDIDATE['name']}",
        "",
        "## Cycle Result",
        f"- Time: {now.isoformat(timespec='seconds')}",
        f"- Data ready: {'YES' if ready else 'NO'}",
        f"- Readiness reason: {readiness_reason}",
        f"- Signal: {signal_text}",
        f"- SMC direction reason: {signal.pe_reason if signal else readiness_reason}",
        f"- Entry: {signal.entry if signal else ''}",
        f"- SL: {signal.stop_loss if signal else ''}",
        f"- Target: {signal.target if signal else ''}",
        f"- Exit reason: {event.get('exit_reason', '')}",
        f"- Paper PnL: {event.get('paper_pnl', 0.0)}",
        f"- Position state: {state.get('status', 'UNKNOWN')}",
        f"- Ledger/evaluator status: {ledger_status}",
        "",
        "## Machine Event",
        "```json",
        json.dumps(event, indent=2, sort_keys=True),
        "```",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_one_cycle(paths: SupervisorPaths, now: datetime) -> dict[str, Any]:
    assert_safety_contract()
    paths.out_dir.mkdir(parents=True, exist_ok=True)

    index_candles = read_candles(paths.index_csv, premium=False)
    premium_candles = read_candles(paths.premium_csv, premium=True)
    ready, readiness_reason = data_ready(index_candles, premium_candles, now)

    state = load_position_state(paths.state_json)
    signal: SignalDecision | None = None
    event: dict[str, Any] = {
        "module": MODULE_ID,
        "event": "NO_SIGNAL",
        "signal_generated": False,
        "readiness_reason": readiness_reason,
        "exit_reason": "",
        "paper_pnl": 0.0,
        "paper_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
    }

    if ready:
        if state.get("status") == "OPEN":
            latest_premium = select_position_premium_candle(
                premium_candles,
                state,
            )

            if latest_premium is None:
                event.update(
                    {
                        "event": "POSITION_HELD",
                        "exit_reason": "ACTIVE_OPTION_CANDLE_MISSING",
                        "paper_pnl": 0.0,
                        "status": "OPEN",
                        "side": state.get("side", ""),
                        "option_symbol": state.get("option_symbol", ""),
                    }
                )
            else:
                state, event = evaluate_open_position(
                    state,
                    latest_premium,
                    now,
                )
                event.update({"module": MODULE_ID, "paper_only": True})
        else:
            signal = evaluate_active_smc_candidate(paths.index_csv, paths.premium_csv, index_candles, premium_candles)
            event.update(
                {
                    "signal_generated": signal.signal_generated,
                    "pe_reason": signal.pe_reason,
                    "entry": signal.entry,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target,
                    "er20": None if signal.er20 is None else round(signal.er20, 6),
                    "dte": signal.dte,
                    "last_traded_price": signal.ltp,
                }
            )
            if signal.signal_generated:
                signal_side = (
                    "CE_BUY"
                    if "OPTION_SIDE=CE_BUY" in signal.pe_reason
                    else "PE_BUY"
                )

                selected_premium = next(
                    (
                        candle
                        for candle in reversed(premium_candles)
                        if candle.signal_side == signal_side
                    ),
                    None,
                )

                state = {
                    "status": "OPEN",
                    "paper_only": True,
                    "module": MODULE_ID,
                    "side": signal_side,
                    "option_symbol": (
                        selected_premium.symbol
                        if selected_premium is not None
                        else ""
                    ),
                    "candidate": (
                        ACTIVE_SMC_CANDIDATE["name"]
                        if "SMC_DECISION=" in signal.pe_reason
                        else LOCKED_CANDIDATE["name"]
                    ),
                    "entry_time": now.isoformat(timespec="seconds"),
                    "entry": signal.entry,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target,
                    "quantity": 1,
                    "broker_execution_allowed": False,
                    "real_orders_allowed": False,
                    "auto_trading_allowed": False,
                    "real_money_allowed": False,
                }
                event["signal_side"] = state["side"]
                event["side"] = state["side"]
                event["option_symbol"] = state["option_symbol"]
                event["direction_reason"] = signal.pe_reason
                event["candidate"] = (
                    ACTIVE_SMC_CANDIDATE["name"]
                    if "SMC_DECISION=" in signal.pe_reason
                    else LOCKED_CANDIDATE["name"]
                )
                event["event"] = "POSITION_OPENED"
                event["exit_reason"] = ""
            else:
                state = {
                    **state,
                    "status": "FLAT",
                    "paper_only": True,
                    "module": MODULE_ID,
                    "last_no_signal_reason": signal.pe_reason,
                    "broker_execution_allowed": False,
                    "real_orders_allowed": False,
                    "auto_trading_allowed": False,
                }

    save_json(paths.state_json, state)

    reason_log = paths.out_dir / "MODULE_131_SIGNAL_REASON_LOG.csv"
    append_csv(
        reason_log,
        {
            "timestamp": now.isoformat(timespec="seconds"),
            "module": MODULE_ID,
            "data_ready": "YES" if ready else "NO",
            "readiness_reason": readiness_reason,
            "signal_generated": "YES" if event.get("signal_generated") else "NO",
            "event": event.get("event", ""),
            "pe_reason": event.get("pe_reason", readiness_reason),
            "entry": event.get("entry", ""),
            "stop_loss": event.get("stop_loss", ""),
            "target": event.get("target", ""),
            "exit_reason": event.get("exit_reason", ""),
            "paper_pnl": event.get("paper_pnl", 0.0),
            "position_state": state.get("status", "UNKNOWN"),
        },
        [
            "timestamp",
            "module",
            "data_ready",
            "readiness_reason",
            "signal_generated",
            "event",
            "pe_reason",
            "entry",
            "stop_loss",
            "target",
            "exit_reason",
            "paper_pnl",
            "position_state",
        ],
    )

    if event.get("event") in {"POSITION_OPENED", "POSITION_CLOSED"}:
        append_csv(
            paths.ledger_csv,
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "module": MODULE_ID,
                "event": event.get("event", ""),
                "side": state.get("side", event.get("side", "PE_BUY")),
                "entry": event.get("entry", state.get("entry", "")),
                "stop_loss": event.get("stop_loss", state.get("stop_loss", "")),
                "target": event.get("target", state.get("target", "")),
                "exit_reason": event.get("exit_reason", ""),
                "paper_pnl": event.get("paper_pnl", 0.0),
                "paper_only": True,
            },
            [
                "timestamp",
                "module",
                "event",
                "side",
                "entry",
                "stop_loss",
                "target",
                "exit_reason",
                "paper_pnl",
                "paper_only",
            ],
        )

    ledger_status = evaluator_status_text(paths.ledger_csv)
    report_path = paths.out_dir / "MODULE_131_INTRADAY_SUPERVISOR_REPORT.md"
    write_report(
        report_path,
        now=now,
        ready=ready,
        readiness_reason=readiness_reason,
        signal=signal,
        event=event,
        state=state,
        ledger_status=ledger_status,
    )

    summary = {
        "module": MODULE_ID,
        "module_name": MODULE_NAME,
        "paper_only": True,
        "locked_candidate": event.get(
            "candidate",
            (
                ACTIVE_SMC_CANDIDATE["name"]
                if "SMC_DECISION=" in str(
                    event.get("pe_reason", "")
                )
                else LOCKED_CANDIDATE["name"]
            ),
        ),
        "data_ready": ready,
        "readiness_reason": readiness_reason,
        "signal_generated": bool(event.get("signal_generated")),
        "signal_side": event.get(
            "signal_side",
            state.get("side", "NO_TRADE"),
        ),
        "event": event.get("event", ""),
        "direction_reason": event.get(
            "direction_reason",
            event.get("pe_reason", readiness_reason),
        ),
        "pe_reason": event.get("pe_reason", readiness_reason),
        "entry": event.get("entry", state.get("entry", "")),
        "stop_loss": event.get("stop_loss", state.get("stop_loss", "")),
        "target": event.get("target", state.get("target", "")),
        "exit_reason": event.get("exit_reason", ""),
        "paper_pnl": event.get("paper_pnl", 0.0),
        "position_state": state.get("status", "UNKNOWN"),
        "ledger_evaluator_status": ledger_status,
        "report": str(report_path),
        "state_json": str(paths.state_json),
        "reason_log": str(reason_log),
        "ledger_csv": str(paths.ledger_csv),
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "auto_trading_allowed": False,
        "real_money_allowed": False,
    }
    save_json(paths.out_dir / "MODULE_131_SUPERVISOR_SUMMARY.json", summary)
    return summary


def default_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("D:/HQE_BACKTEST_RUNS") / f"HQE_MODULE_131_FORWARD_INTRADAY_PAPER_SUPERVISOR_{stamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=MODULE_NAME)
    parser.add_argument("--index-csv", type=Path, default=Path("data/processed/fyers_nifty_5m_normalized.csv"))
    parser.add_argument("--premium-csv", type=Path, default=Path("data/processed/fyers_nifty_option_premium_5m_normalized.csv"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--state-json", type=Path, default=None)
    parser.add_argument("--ledger-csv", type=Path, default=None)
    parser.add_argument("--now", type=str, default=None)
    parser.add_argument("--max-cycles", type=int, default=1)
    parser.add_argument("--cycle-seconds", type=int, default=DEFAULT_CYCLE_SECONDS)
    return parser


def resolve_paths(args: argparse.Namespace) -> SupervisorPaths:
    out_dir = args.out_dir or default_out_dir()
    state_json = args.state_json or (out_dir / "MODULE_131_POSITION_STATE.json")
    ledger_csv = args.ledger_csv or (out_dir / "MODULE_131_PAPER_LEDGER.csv")
    return SupervisorPaths(
        index_csv=args.index_csv,
        premium_csv=args.premium_csv,
        out_dir=out_dir,
        state_json=state_json,
        ledger_csv=ledger_csv,
    )


def main() -> int:
    args = build_parser().parse_args()
    assert_safety_contract()
    paths = resolve_paths(args)
    max_cycles = max(1, int(args.max_cycles))
    cycle_seconds = max(1, int(args.cycle_seconds))

    latest_summary: dict[str, Any] = {}
    for cycle_number in range(max_cycles):
        now = parse_dt(args.now) if args.now else datetime.now()
        latest_summary = run_one_cycle(paths, now)
        latest_summary["cycle_number"] = cycle_number + 1
        if cycle_number < max_cycles - 1:
            time.sleep(cycle_seconds)

    print(json.dumps(latest_summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
