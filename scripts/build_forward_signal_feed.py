"""
HQE Forward Signal Feed Builder

Paper/simulation only.

Builds a locked-candidate scenario/signal CSV for the Forward Paper Auto Runner.

Flow:
index candles + option premium candles
-> locked candidate signal/scenario CSV
-> Forward Paper Auto Runner
-> paper trades + reason report

Forbidden:
- broker execution
- real orders
- real money
- auto trading approval
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable


LOCKED_CANDIDATE_NAME = (
    "ER20_GE_030 + PE only + DTE >= 1 + "
    "last_traded_price 20-200 + SL040_TGT120"
)

DEFAULT_MIN_ER20 = 0.30
DEFAULT_MIN_PREMIUM = 20.0
DEFAULT_MAX_PREMIUM = 200.0
DEFAULT_MIN_DTE = 1
DEFAULT_SIDE = "PE_BUY"

SAFETY = {
    "paper_simulation_only": "YES",
    "real_money": "NO",
    "broker_execution": "NO",
    "real_orders": "NO",
    "auto_trading": "NO",
    "paper_live": "NOT_YET",
    "option_selling": "NO",
}


OUTPUT_FIELDS = [
    "scenario_id",
    "signal_time",
    "entry_time",
    "date",
    "symbol",
    "option_symbol",
    "side",
    "signal_side",
    "option_type",
    "expiry_week",
    "expiry",
    "dte",
    "last_traded_price",
    "entry_price",
    "premium",
    "er20",
    "stop_loss_percent",
    "target_percent",
    "rationale",
    "reason",
    "rule_match",
    "data_quality_ok",
    "manual_override",
]


@dataclass(frozen=True)
class IndexSignalState:
    signal_time: str
    er20: float
    candle_range: float
    prior_20_avg_range: float
    reason: str


def _norm_key(value: str) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _normalized_row(row: dict[str, str]) -> dict[str, str]:
    return {_norm_key(str(k)): "" if v is None else str(v).strip() for k, v in row.items()}


def _first(row: dict[str, str], names: Iterable[str], default: str = "") -> str:
    normalized = _normalized_row(row)
    for name in names:
        value = normalized.get(_norm_key(name), "")
        if value != "":
            return value
    return default


def _parse_float(value: str) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_intish(value: str) -> int | None:
    number = _parse_float(value)
    if number is None:
        return None
    return int(number)


def _parse_datetime(value: str, fallback_date: str = "") -> datetime | None:
    text = (value or "").strip()
    if text == "":
        return None

    if fallback_date and len(text) <= 8 and ":" in text:
        text = f"{fallback_date.strip()} {text}"

    text = text.replace("T", " ")
    text = text.replace("/", "-")

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(text[: len(fmt)], fmt)
            return parsed
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _format_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def infer_datetime(row: dict[str, str]) -> datetime | None:
    date_text = _first(row, ["date", "trade_date", "candle_date"])
    time_text = _first(
        row,
        [
            "signal_time",
            "entry_time",
            "timestamp",
            "datetime",
            "date_time",
            "candle_time",
            "bar_time",
            "time",
        ],
    )

    parsed = _parse_datetime(time_text, fallback_date=date_text)
    if parsed is not None:
        return parsed

    return _parse_datetime(date_text)


def infer_symbol(row: dict[str, str]) -> str:
    return _first(
        row,
        [
            "symbol",
            "tradingsymbol",
            "trading_symbol",
            "instrument",
            "instrument_key",
            "option_symbol",
            "contract",
        ],
    )


def infer_option_type(row: dict[str, str]) -> str:
    explicit = _first(row, ["option_type", "instrument_type", "type", "side"])
    symbol = infer_symbol(row)
    text = f"{explicit} {symbol}".upper().replace(" ", "_").replace("-", "_")

    if "PE_BUY" in text or "PUT_BUY" in text:
        return "PE"
    if "CE_BUY" in text or "CALL_BUY" in text:
        return "CE"
    if "PE" in text or "PUT" in text:
        return "PE"
    if "CE" in text or "CALL" in text:
        return "CE"
    return ""


def infer_price(row: dict[str, str]) -> float | None:
    value = _first(
        row,
        [
            "last_traded_price",
            "ltp",
            "premium",
            "entry_price",
            "option_price",
            "close",
            "close_price",
        ],
    )
    return _parse_float(value)


def infer_expiry(row: dict[str, str]) -> str:
    return _first(row, ["expiry_week", "expiry", "expiry_date", "contract_expiry"])


def infer_dte(row: dict[str, str], signal_dt: datetime | None) -> int | None:
    explicit = _first(row, ["dte", "days_to_expiry", "days_until_expiry"])
    parsed = _parse_intish(explicit)
    if parsed is not None:
        return parsed

    expiry_text = infer_expiry(row)
    expiry_dt = _parse_datetime(expiry_text)
    if expiry_dt is None or signal_dt is None:
        return None

    return (expiry_dt.date() - signal_dt.date()).days


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        return list(reader), fieldnames


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compute_index_er20_states(
    index_rows: list[dict[str, str]],
    *,
    min_er20: float,
) -> dict[str, IndexSignalState]:
    parsed_rows: list[tuple[datetime, float]] = []

    for row in index_rows:
        dt = infer_datetime(row)
        high = _parse_float(_first(row, ["high", "high_price"]))
        low = _parse_float(_first(row, ["low", "low_price"]))
        if dt is None or high is None or low is None:
            continue

        candle_range = max(0.0, high - low)
        parsed_rows.append((dt, candle_range))

    parsed_rows.sort(key=lambda item: item[0])

    states: dict[str, IndexSignalState] = {}
    ranges = [item[1] for item in parsed_rows]

    for index, (dt, candle_range) in enumerate(parsed_rows):
        if index < 20:
            continue

        prior_ranges = ranges[index - 20 : index]
        prior_avg = sum(prior_ranges) / len(prior_ranges) if prior_ranges else 0.0
        if prior_avg <= 0:
            continue

        er20 = candle_range / prior_avg
        if er20 >= min_er20:
            key = _format_dt(dt)
            states[key] = IndexSignalState(
                signal_time=key,
                er20=er20,
                candle_range=candle_range,
                prior_20_avg_range=prior_avg,
                reason=(
                    f"index_range_expansion_ok: candle_range={candle_range:.2f}, "
                    f"prior_20_avg_range={prior_avg:.2f}, er20={er20:.4f}"
                ),
            )

    return states


def _within_date_window(
    dt: datetime,
    *,
    only_date: str,
    start_time: str,
    end_time: str,
) -> bool:
    if only_date and dt.date().isoformat() != only_date:
        return False

    if start_time:
        parsed_start = time.fromisoformat(start_time)
        if dt.time() < parsed_start:
            return False

    if end_time:
        parsed_end = time.fromisoformat(end_time)
        if dt.time() > parsed_end:
            return False

    return True


def build_forward_signal_feed(
    *,
    index_csv: Path,
    premium_csv: Path,
    output_csv: Path,
    report_json: Path,
    report_md: Path,
    only_date: str = "",
    start_time: str = "",
    end_time: str = "",
    min_er20: float = DEFAULT_MIN_ER20,
    min_premium: float = DEFAULT_MIN_PREMIUM,
    max_premium: float = DEFAULT_MAX_PREMIUM,
    min_dte: int = DEFAULT_MIN_DTE,
    max_signals: int = 0,
) -> dict[str, object]:
    index_rows, _ = read_csv_rows(index_csv)
    premium_rows, _ = read_csv_rows(premium_csv)

    index_states = compute_index_er20_states(index_rows, min_er20=min_er20)

    output_rows: list[dict[str, str]] = []
    rejected_counts = {
        "missing_time": 0,
        "date_window": 0,
        "no_index_er20_match": 0,
        "not_pe": 0,
        "missing_price": 0,
        "premium_outside_range": 0,
        "missing_dte": 0,
        "dte_below_minimum": 0,
        "duplicate": 0,
    }

    seen_keys: set[tuple[str, str, str]] = set()

    for row in premium_rows:
        dt = infer_datetime(row)
        if dt is None:
            rejected_counts["missing_time"] += 1
            continue

        if not _within_date_window(
            dt,
            only_date=only_date,
            start_time=start_time,
            end_time=end_time,
        ):
            rejected_counts["date_window"] += 1
            continue

        signal_time = _format_dt(dt)
        index_state = index_states.get(signal_time)
        if index_state is None:
            rejected_counts["no_index_er20_match"] += 1
            continue

        option_type = infer_option_type(row)
        if option_type != "PE":
            rejected_counts["not_pe"] += 1
            continue

        price = infer_price(row)
        if price is None:
            rejected_counts["missing_price"] += 1
            continue
        if price < min_premium or price > max_premium:
            rejected_counts["premium_outside_range"] += 1
            continue

        dte = infer_dte(row, dt)
        if dte is None:
            rejected_counts["missing_dte"] += 1
            continue
        if dte < min_dte:
            rejected_counts["dte_below_minimum"] += 1
            continue

        symbol = infer_symbol(row)
        expiry = infer_expiry(row)

        dedupe_key = (signal_time, symbol, "PE_BUY")
        if dedupe_key in seen_keys:
            rejected_counts["duplicate"] += 1
            continue
        seen_keys.add(dedupe_key)

        scenario_id = f"FWD-SIG-{len(output_rows) + 1:06d}"
        reason = (
            f"accepted_locked_candidate: PE_BUY; DTE={dte}>=1; "
            f"premium={price:g} in 20-200; ER20={index_state.er20:.4f}>=0.30; "
            f"{index_state.reason}; candidate={LOCKED_CANDIDATE_NAME}"
        )

        output_rows.append(
            {
                "scenario_id": scenario_id,
                "signal_time": signal_time,
                "entry_time": signal_time,
                "date": dt.date().isoformat(),
                "symbol": symbol,
                "option_symbol": symbol,
                "side": "PE_BUY",
                "signal_side": "PE_BUY",
                "option_type": "PE",
                "expiry_week": expiry,
                "expiry": expiry,
                "dte": str(dte),
                "last_traded_price": f"{price:g}",
                "entry_price": f"{price:g}",
                "premium": f"{price:g}",
                "er20": f"{index_state.er20:.6f}",
                "stop_loss_percent": "0.40",
                "target_percent": "1.20",
                "rationale": reason,
                "reason": reason,
                "rule_match": "YES",
                "data_quality_ok": "YES",
                "manual_override": "NO",
            }
        )

        if max_signals and len(output_rows) >= max_signals:
            break

    output_rows.sort(key=lambda item: (item["signal_time"], item["symbol"]))
    write_csv_rows(output_csv, OUTPUT_FIELDS, output_rows)

    status = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "decision": (
            "FORWARD_SIGNAL_FEED_CREATED"
            if output_rows
            else "NO_LOCKED_CANDIDATE_SIGNALS_FOUND"
        ),
        "locked_candidate": LOCKED_CANDIDATE_NAME,
        "safety": SAFETY,
        "index_csv": str(index_csv),
        "premium_csv": str(premium_csv),
        "output_csv": str(output_csv),
        "only_date": only_date,
        "start_time": start_time,
        "end_time": end_time,
        "min_er20": min_er20,
        "min_premium": min_premium,
        "max_premium": max_premium,
        "min_dte": min_dte,
        "index_er20_times": len(index_states),
        "premium_rows": len(premium_rows),
        "signals_created": len(output_rows),
        "rejected_counts": rejected_counts,
    }

    report_json.write_text(json.dumps(status, indent=2), encoding="utf-8")

    lines = [
        "# HQE Forward Signal Feed Builder Report",
        "",
        f"Created: {status['created_at']}",
        "",
        "## Decision",
        str(status["decision"]),
        "",
        "## Signals created",
        str(status["signals_created"]),
        "",
        "## Locked candidate",
        LOCKED_CANDIDATE_NAME,
        "",
        "## Inputs",
        f"- Index CSV: {index_csv}",
        f"- Premium CSV: {premium_csv}",
        f"- Output CSV: {output_csv}",
        "",
        "## Filters",
        f"- Date: {only_date or 'ALL'}",
        f"- Start time: {start_time or 'ALL'}",
        f"- End time: {end_time or 'ALL'}",
        f"- ER20 >= {min_er20}",
        f"- PE only",
        f"- DTE >= {min_dte}",
        f"- Premium {min_premium:g}-{max_premium:g}",
        f"- SL 40%",
        f"- Target 120%",
        "",
        "## Rejected counts",
    ]
    for key, value in rejected_counts.items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Safety"])
    for key, value in SAFETY.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Important",
            "This builder creates paper-only signal feed rows. It does not place orders.",
            "Broker execution remains NO.",
            "Real money remains NO.",
        ]
    )

    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build HQE forward paper signal/scenario feed. Paper-only."
    )
    parser.add_argument("--index-csv", required=True)
    parser.add_argument("--premium-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--report-json", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--date", default="")
    parser.add_argument("--start-time", default="")
    parser.add_argument("--end-time", default="")
    parser.add_argument("--min-er20", type=float, default=DEFAULT_MIN_ER20)
    parser.add_argument("--min-premium", type=float, default=DEFAULT_MIN_PREMIUM)
    parser.add_argument("--max-premium", type=float, default=DEFAULT_MAX_PREMIUM)
    parser.add_argument("--min-dte", type=int, default=DEFAULT_MIN_DTE)
    parser.add_argument("--max-signals", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    status = build_forward_signal_feed(
        index_csv=Path(args.index_csv),
        premium_csv=Path(args.premium_csv),
        output_csv=Path(args.output_csv),
        report_json=Path(args.report_json),
        report_md=Path(args.report_md),
        only_date=args.date,
        start_time=args.start_time,
        end_time=args.end_time,
        min_er20=args.min_er20,
        min_premium=args.min_premium,
        max_premium=args.max_premium,
        min_dte=args.min_dte,
        max_signals=args.max_signals,
    )

    print("HQE Forward Signal Feed Builder Complete")
    print("")
    print(f"Decision: {status['decision']}")
    print(f"Signals created: {status['signals_created']}")
    print(f"Output CSV: {status['output_csv']}")
    print(f"Report JSON: {args.report_json}")
    print(f"Report MD: {args.report_md}")
    print("")
    print("Safety:")
    for key, value in SAFETY.items():
        print(f"{key} = {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

