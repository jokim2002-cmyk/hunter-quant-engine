"""
HQE Forward Paper Auto Runner

Paper/simulation only.

This runner is the forward-validation bridge:
- reads a scenario/signal CSV,
- locks the candidate rules,
- writes signal/reason logs,
- optionally invokes the official option-buy backtest runner,
- writes paper trade outputs,
- appends completed paper trades to the forward validation ledger.

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
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


LOCKED_CANDIDATE_NAME = (
    "ER20_GE_030 + PE only + DTE >= 1 + "
    "last_traded_price 20-200 + SL040_TGT120"
)

LOCKED_STOP_LOSS_PERCENT = "0.40"
LOCKED_TARGET_PERCENT = "1.20"
LOCKED_MIN_PREMIUM = 20.0
LOCKED_MAX_PREMIUM = 200.0
LOCKED_MIN_DTE = 1
LOCKED_MIN_ER20 = 0.30

SAFETY = {
    "paper_simulation_only": "YES",
    "real_money": "NO",
    "broker_execution": "NO",
    "real_orders": "NO",
    "auto_trading": "NO",
    "paper_live": "NOT_YET",
    "option_selling": "NO",
}


@dataclass(frozen=True)
class SignalDecision:
    accepted: bool
    reason: str
    side: str
    symbol: str
    signal_time: str
    entry_price: str
    dte: str
    expiry_week: str
    er20: str


def _norm_key(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


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


def infer_side(row: dict[str, str]) -> str:
    explicit = _first(row, ["side", "signal_side", "option_side", "option_type", "type"])
    text = explicit.upper().replace(" ", "_").replace("-", "_")
    symbol = infer_symbol(row).upper()

    combined = f"{text} {symbol}"

    if "PE_BUY" in combined or "PUT_BUY" in combined:
        return "PE_BUY"
    if "CE_BUY" in combined or "CALL_BUY" in combined:
        return "CE_BUY"
    if "PE" in combined or "PUT" in combined:
        return "PE_BUY"
    if "CE" in combined or "CALL" in combined:
        return "CE_BUY"
    return ""


def infer_signal_time(row: dict[str, str]) -> str:
    return _first(
        row,
        [
            "signal_time",
            "entry_time",
            "timestamp",
            "datetime",
            "date_time",
            "time",
            "candle_time",
            "bar_time",
            "date",
        ],
    )


def infer_entry_price(row: dict[str, str]) -> str:
    return _first(
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


def infer_dte(row: dict[str, str]) -> str:
    return _first(row, ["dte", "days_to_expiry", "days_until_expiry"])


def infer_expiry_week(row: dict[str, str]) -> str:
    return _first(row, ["expiry_week", "expiry", "expiry_date", "contract_expiry"])


def infer_er20(row: dict[str, str]) -> str:
    return _first(
        row,
        [
            "er20",
            "er_20",
            "expansion_ratio_20",
            "expansionratio20",
            "range_expansion_20",
        ],
    )


def locked_candidate_decision(row: dict[str, str]) -> SignalDecision:
    side = infer_side(row)
    symbol = infer_symbol(row)
    signal_time = infer_signal_time(row)
    entry_price_text = infer_entry_price(row)
    dte_text = infer_dte(row)
    expiry_week = infer_expiry_week(row)
    er20_text = infer_er20(row)

    reasons: list[str] = []

    if side != "PE_BUY":
        return SignalDecision(
            False,
            f"rejected: locked candidate is PE_BUY only, got side={side or 'UNKNOWN'}",
            side,
            symbol,
            signal_time,
            entry_price_text,
            dte_text,
            expiry_week,
            er20_text,
        )

    price = _parse_float(entry_price_text)
    if price is None:
        return SignalDecision(
            False,
            "rejected: missing option premium/entry price",
            side,
            symbol,
            signal_time,
            entry_price_text,
            dte_text,
            expiry_week,
            er20_text,
        )
    if price < LOCKED_MIN_PREMIUM or price > LOCKED_MAX_PREMIUM:
        return SignalDecision(
            False,
            (
                "rejected: premium outside locked range "
                f"{LOCKED_MIN_PREMIUM:g}-{LOCKED_MAX_PREMIUM:g}, got {price:g}"
            ),
            side,
            symbol,
            signal_time,
            entry_price_text,
            dte_text,
            expiry_week,
            er20_text,
        )
    reasons.append(f"premium_ok={price:g}")

    dte = _parse_intish(dte_text)
    if dte is None:
        return SignalDecision(
            False,
            "rejected: missing DTE for locked DTE>=1 rule",
            side,
            symbol,
            signal_time,
            entry_price_text,
            dte_text,
            expiry_week,
            er20_text,
        )
    if dte < LOCKED_MIN_DTE:
        return SignalDecision(
            False,
            f"rejected: DTE below locked minimum {LOCKED_MIN_DTE}, got {dte}",
            side,
            symbol,
            signal_time,
            entry_price_text,
            dte_text,
            expiry_week,
            er20_text,
        )
    reasons.append(f"dte_ok={dte}")

    er20 = _parse_float(er20_text)
    if er20_text != "" and er20 is not None:
        if er20 < LOCKED_MIN_ER20:
            return SignalDecision(
                False,
                f"rejected: ER20 below locked minimum {LOCKED_MIN_ER20:g}, got {er20:g}",
                side,
                symbol,
                signal_time,
                entry_price_text,
                dte_text,
                expiry_week,
                er20_text,
            )
        reasons.append(f"er20_ok={er20:g}")
    else:
        reasons.append("er20_not_present_in_source_csv_assumed_pre_filtered")

    reasons.append("locked_candidate=PE_DTE_GE_1_PREM_20_200_SL040_TGT120")
    return SignalDecision(
        True,
        "accepted: " + "; ".join(reasons),
        side,
        symbol,
        signal_time,
        entry_price_text,
        dte_text,
        expiry_week,
        er20_text,
    )


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


def build_signal_log(
    scenario_csv: Path,
    locked_scenario_csv: Path,
    signal_log_csv: Path,
    rejected_signal_log_csv: Path,
) -> dict[str, int]:
    rows, fieldnames = read_csv_rows(scenario_csv)
    accepted_rows: list[dict[str, str]] = []
    signal_rows: list[dict[str, str]] = []
    rejected_rows: list[dict[str, str]] = []

    for index, row in enumerate(rows, start=1):
        decision = locked_candidate_decision(row)
        log_row = {
            "signal_id": f"SIG-{index:06d}",
            "source_row_number": str(index),
            "accepted": "YES" if decision.accepted else "NO",
            "signal_time": decision.signal_time,
            "side": decision.side,
            "symbol": decision.symbol,
            "expiry_week": decision.expiry_week,
            "dte": decision.dte,
            "entry_price": decision.entry_price,
            "stop_loss_percent": LOCKED_STOP_LOSS_PERCENT,
            "target_percent": LOCKED_TARGET_PERCENT,
            "reason": decision.reason,
            "rule_match": "YES" if decision.accepted else "NO",
            "data_quality_ok": "YES" if decision.accepted else "NO",
            "manual_override": "NO",
        }
        if decision.accepted:
            accepted_rows.append(row)
            signal_rows.append(log_row)
        else:
            rejected_rows.append(log_row)

    write_csv_rows(locked_scenario_csv, fieldnames, accepted_rows)
    signal_fields = [
        "signal_id",
        "source_row_number",
        "accepted",
        "signal_time",
        "side",
        "symbol",
        "expiry_week",
        "dte",
        "entry_price",
        "stop_loss_percent",
        "target_percent",
        "reason",
        "rule_match",
        "data_quality_ok",
        "manual_override",
    ]
    write_csv_rows(signal_log_csv, signal_fields, signal_rows)
    write_csv_rows(rejected_signal_log_csv, signal_fields, rejected_rows)

    return {
        "source_rows": len(rows),
        "accepted_signals": len(signal_rows),
        "rejected_signals": len(rejected_rows),
    }


def run_official_runner(
    runner: Path,
    premium_csv: Path,
    locked_scenario_csv: Path,
    out_dir: Path,
    max_bars_held: str,
    min_estimated_net_reward: str,
    entry_slippage_percent: str,
    exit_slippage_percent: str,
) -> dict[str, Path | str | int]:
    summary_json = out_dir / "official_summary.json"
    summary_csv = out_dir / "official_summary.csv"
    trades_json = out_dir / "official_trades.json"
    trades_csv = out_dir / "FORWARD_AUTO_PAPER_TRADES.csv"
    command_txt = out_dir / "OFFICIAL_RUNNER_COMMAND.txt"
    stdout_txt = out_dir / "OFFICIAL_RUNNER_STDOUT.txt"
    stderr_txt = out_dir / "OFFICIAL_RUNNER_STDERR.txt"

    cmd = [
        sys.executable,
        str(runner),
        "--scenario-csv",
        str(locked_scenario_csv),
        "--premium-csv",
        str(premium_csv),
        "--summary-json",
        str(summary_json),
        "--summary-csv",
        str(summary_csv),
        "--trades-json",
        str(trades_json),
        "--trades-csv",
        str(trades_csv),
        "--stop-loss-percent",
        LOCKED_STOP_LOSS_PERCENT,
        "--target-percent",
        LOCKED_TARGET_PERCENT,
        "--entry-slippage-percent",
        entry_slippage_percent,
        "--exit-slippage-percent",
        exit_slippage_percent,
        "--cost-profile",
        "fyers-nifty-options-intraday",
        "--time-scope-premium-candles",
        "--max-bars-held",
        max_bars_held,
        "--min-estimated-net-reward",
        min_estimated_net_reward,
    ]
    command_txt.write_text(" ".join(cmd), encoding="utf-8")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stdout_txt.write_text(result.stdout, encoding="utf-8")
    stderr_txt.write_text(result.stderr, encoding="utf-8")

    if result.returncode != 0:
        raise RuntimeError(
            "Official runner failed. See "
            f"{stderr_txt} and {stdout_txt}. Return code={result.returncode}"
        )

    return {
        "returncode": result.returncode,
        "summary_json": summary_json,
        "summary_csv": summary_csv,
        "trades_json": trades_json,
        "trades_csv": trades_csv,
        "command_txt": command_txt,
    }


LEDGER_FIELDS = [
    "date",
    "day_number",
    "trade_number",
    "expiry_week",
    "symbol",
    "side",
    "entry_time",
    "entry_price",
    "exit_time",
    "exit_price",
    "quantity",
    "gross_pnl",
    "estimated_charges",
    "net_pnl",
    "exit_reason",
    "rule_match",
    "data_quality_ok",
    "manual_override",
    "notes",
]


def _ledger_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row.get("date", ""),
        row.get("symbol", ""),
        row.get("side", ""),
        row.get("entry_time", ""),
        row.get("entry_price", ""),
        row.get("exit_time", ""),
        row.get("exit_price", ""),
        row.get("net_pnl", ""),
    )


def _date_from_time(value: str) -> str:
    text = (value or "").strip()
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return text[:10]
    return text


def map_trade_to_ledger_row(row: dict[str, str], day_number: str, trade_number: int) -> dict[str, str]:
    entry_time = _first(row, ["entry_time", "signal_time", "entry_timestamp", "timestamp", "time"])
    exit_time = _first(row, ["exit_time", "exit_timestamp"])
    date = _first(row, ["date", "trade_date"], default=_date_from_time(entry_time or exit_time))

    symbol = infer_symbol(row)
    side = infer_side(row)
    entry_price = _first(row, ["entry_price", "fill_entry_price", "entry", "buy_price"])
    exit_price = _first(row, ["exit_price", "fill_exit_price", "exit", "sell_price"])
    expiry_week = infer_expiry_week(row)

    gross = _first(row, ["gross_pnl", "gross", "gross_profit", "pnl_before_charges"])
    charges = _first(row, ["estimated_charges", "charges", "costs", "total_charges"])
    net = _first(row, ["net_pnl", "net", "net_profit", "pnl_after_charges"])
    exit_reason = _first(row, ["exit_reason", "reason", "status"])

    return {
        "date": date,
        "day_number": day_number,
        "trade_number": str(trade_number),
        "expiry_week": expiry_week,
        "symbol": symbol,
        "side": side or "PE_BUY",
        "entry_time": entry_time,
        "entry_price": entry_price,
        "exit_time": exit_time,
        "exit_price": exit_price,
        "quantity": _first(row, ["quantity", "qty", "lots"], default="paper_only"),
        "gross_pnl": gross,
        "estimated_charges": charges,
        "net_pnl": net,
        "exit_reason": exit_reason,
        "rule_match": "YES",
        "data_quality_ok": "YES",
        "manual_override": "NO",
        "notes": f"auto_runner_locked_candidate={LOCKED_CANDIDATE_NAME}",
    }


def append_trades_to_master_ledger(
    trades_csv: Path,
    master_ledger_csv: Path,
    day_number: str,
) -> dict[str, int]:
    if not trades_csv.exists():
        return {"official_trade_rows": 0, "rows_appended": 0, "duplicates_skipped": 0}

    trade_rows, _ = read_csv_rows(trades_csv)
    master_ledger_csv.parent.mkdir(parents=True, exist_ok=True)

    existing_rows: list[dict[str, str]] = []
    if master_ledger_csv.exists():
        existing_rows, _ = read_csv_rows(master_ledger_csv)

    existing_keys = {_ledger_key(row) for row in existing_rows if any(row.values())}
    rows_to_append: list[dict[str, str]] = []
    duplicates = 0

    next_trade_number = len([row for row in existing_rows if row.get("trade_number", "")]) + 1
    for row in trade_rows:
        mapped = map_trade_to_ledger_row(row, day_number=day_number, trade_number=next_trade_number)
        key = _ledger_key(mapped)
        if key in existing_keys:
            duplicates += 1
            continue
        rows_to_append.append(mapped)
        existing_keys.add(key)
        next_trade_number += 1

    write_header = not master_ledger_csv.exists() or master_ledger_csv.stat().st_size == 0
    with master_ledger_csv.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows_to_append)

    return {
        "official_trade_rows": len(trade_rows),
        "rows_appended": len(rows_to_append),
        "duplicates_skipped": duplicates,
    }


def write_open_positions(path: Path) -> None:
    fields = [
        "position_id",
        "signal_id",
        "side",
        "symbol",
        "entry_time",
        "entry_price",
        "stop_loss_price",
        "target_price",
        "status",
        "notes",
    ]
    write_csv_rows(path, fields, [])


def write_daily_report(
    path: Path,
    status: dict[str, object],
    signal_counts: dict[str, int],
    ledger_counts: dict[str, int],
) -> None:
    lines = [
        "# HQE Forward Auto Paper Daily Reason Report",
        "",
        f"Created: {status['created_at']}",
        "",
        "## Decision",
        str(status["decision"]),
        "",
        "## Locked candidate",
        LOCKED_CANDIDATE_NAME,
        "",
        "## Signal filter counts",
        f"- Source rows: {signal_counts['source_rows']}",
        f"- Accepted paper signals: {signal_counts['accepted_signals']}",
        f"- Rejected rows: {signal_counts['rejected_signals']}",
        "",
        "## Paper trade output",
        f"- Official trade rows: {ledger_counts['official_trade_rows']}",
        f"- Rows appended to master ledger: {ledger_counts['rows_appended']}",
        f"- Duplicates skipped: {ledger_counts['duplicates_skipped']}",
        "",
        "## Safety",
    ]
    for key, value in SAFETY.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Important",
            "This module is paper/simulation only. It does not place broker orders.",
            "Real money remains NO.",
            "Broker execution remains NO.",
            "",
            "## Files",
        ]
    )
    for key in [
        "signal_log_csv",
        "rejected_signal_log_csv",
        "locked_scenario_csv",
        "trades_csv",
        "open_positions_csv",
        "master_ledger_csv",
    ]:
        lines.append(f"- {key}: {status.get(key, '')}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HQE forward paper auto runner. Paper/simulation only."
    )
    parser.add_argument("--scenario-csv", required=True, help="Source scenario/signal CSV")
    parser.add_argument("--premium-csv", required=True, help="Premium candles CSV")
    parser.add_argument("--active-dir", required=True, help="Active forward validation folder")
    parser.add_argument(
        "--runner",
        default="scripts/run_option_buy_backtest.py",
        help="Official option-buy backtest runner path",
    )
    parser.add_argument("--day-number", default="AUTO", help="Forward day number")
    parser.add_argument("--max-bars-held", default="75")
    parser.add_argument("--min-estimated-net-reward", default="0")
    parser.add_argument("--entry-slippage-percent", default="0")
    parser.add_argument("--exit-slippage-percent", default="0")
    parser.add_argument(
        "--skip-official-runner",
        action="store_true",
        help="Only build signal/reason logs; used for dry-run/tests.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    scenario_csv = Path(args.scenario_csv)
    premium_csv = Path(args.premium_csv)
    active_dir = Path(args.active_dir)
    runner = Path(args.runner)
    if not runner.is_absolute():
        runner = Path.cwd() / runner

    if not scenario_csv.exists():
        raise FileNotFoundError(f"Scenario CSV not found: {scenario_csv}")
    if not premium_csv.exists():
        raise FileNotFoundError(f"Premium CSV not found: {premium_csv}")
    if not active_dir.exists():
        raise FileNotFoundError(f"Active folder not found: {active_dir}")
    if not args.skip_official_runner and not runner.exists():
        raise FileNotFoundError(f"Official runner not found: {runner}")

    out_dir = active_dir / ("FORWARD_AUTO_RUN_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)

    locked_scenario_csv = out_dir / "LOCKED_CANDIDATE_SCENARIO.csv"
    signal_log_csv = out_dir / "FORWARD_AUTO_SIGNAL_LOG.csv"
    rejected_signal_log_csv = out_dir / "FORWARD_AUTO_REJECTED_SIGNAL_LOG.csv"
    open_positions_csv = out_dir / "FORWARD_AUTO_OPEN_POSITIONS.csv"
    daily_report_md = out_dir / "FORWARD_AUTO_DAILY_REASON_REPORT.md"
    status_json = out_dir / "FORWARD_AUTO_STATUS.json"
    master_ledger_csv = active_dir / "FORWARD_VALIDATION_MASTER_LEDGER.csv"

    signal_counts = build_signal_log(
        scenario_csv=scenario_csv,
        locked_scenario_csv=locked_scenario_csv,
        signal_log_csv=signal_log_csv,
        rejected_signal_log_csv=rejected_signal_log_csv,
    )

    runner_outputs: dict[str, object] = {}
    trades_csv = out_dir / "FORWARD_AUTO_PAPER_TRADES.csv"

    if signal_counts["accepted_signals"] > 0 and not args.skip_official_runner:
        runner_outputs = run_official_runner(
            runner=runner,
            premium_csv=premium_csv,
            locked_scenario_csv=locked_scenario_csv,
            out_dir=out_dir,
            max_bars_held=args.max_bars_held,
            min_estimated_net_reward=args.min_estimated_net_reward,
            entry_slippage_percent=args.entry_slippage_percent,
            exit_slippage_percent=args.exit_slippage_percent,
        )
        trades_csv = Path(str(runner_outputs["trades_csv"]))
    else:
        write_csv_rows(trades_csv, LEDGER_FIELDS, [])

    ledger_counts = append_trades_to_master_ledger(
        trades_csv=trades_csv,
        master_ledger_csv=master_ledger_csv,
        day_number=str(args.day_number),
    )
    write_open_positions(open_positions_csv)

    decision = (
        "FORWARD_AUTO_PAPER_RUN_COMPLETE"
        if signal_counts["accepted_signals"] > 0
        else "NO_LOCKED_CANDIDATE_SIGNAL_FOUND"
    )

    status = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "decision": decision,
        "locked_candidate": LOCKED_CANDIDATE_NAME,
        "safety": SAFETY,
        "source_scenario_csv": str(scenario_csv),
        "premium_csv": str(premium_csv),
        "active_dir": str(active_dir),
        "run_output_dir": str(out_dir),
        "signal_counts": signal_counts,
        "ledger_counts": ledger_counts,
        "signal_log_csv": str(signal_log_csv),
        "rejected_signal_log_csv": str(rejected_signal_log_csv),
        "locked_scenario_csv": str(locked_scenario_csv),
        "trades_csv": str(trades_csv),
        "open_positions_csv": str(open_positions_csv),
        "master_ledger_csv": str(master_ledger_csv),
        "runner_outputs": {key: str(value) for key, value in runner_outputs.items()},
    }

    status_json.write_text(json.dumps(status, indent=2), encoding="utf-8")
    write_daily_report(daily_report_md, status, signal_counts, ledger_counts)

    print("HQE Forward Paper Auto Runner Complete")
    print("")
    print(f"Decision: {decision}")
    print(f"Output folder: {out_dir}")
    print(f"Signal log: {signal_log_csv}")
    print(f"Rejected signal log: {rejected_signal_log_csv}")
    print(f"Paper trades: {trades_csv}")
    print(f"Open positions: {open_positions_csv}")
    print(f"Daily reason report: {daily_report_md}")
    print(f"Status JSON: {status_json}")
    print(f"Master ledger: {master_ledger_csv}")
    print("")
    print("Safety:")
    for key, value in SAFETY.items():
        print(f"{key} = {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
