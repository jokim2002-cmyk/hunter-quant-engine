from __future__ import annotations

import argparse
import csv
import html
import json
import tempfile
from bisect import bisect_right
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hqe_fyers_option_chain_data_only import (
    SAFETY_LOCK,
    build_fyers_client,
)
from hqe_smc_live_direction import (
    _run_gate,
    map_decision,
)

MODULE_VERSION = "HQE_CURRENT_DAY_RECORDED_REPLAY_EVALUATION_V1"
INDEX_SYMBOL = "NSE:NIFTY50-INDEX"
INDEX_RESOLUTION = "5"
MIN_HISTORY_BARS = 21
MIN_ER20 = 0.30
MIN_DTE = 1
MIN_PREMIUM = 20.0
MAX_PREMIUM = 200.0

REPLAY_SAFETY = {
    **SAFETY_LOCK,
    "recorded_data_replay": True,
    "evaluation_only": True,
    "no_position_opening": True,
    "no_pnl_calculation": True,
}


class RecordedReplayError(RuntimeError):
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


def _parse_timestamp(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None

    if parsed is None:
        for pattern in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
        ):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue

    if parsed is None:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def history_request(trading_date: str) -> dict[str, str]:
    try:
        date.fromisoformat(trading_date)
    except ValueError as exc:
        raise RecordedReplayError(
            "Trading date must use YYYY-MM-DD."
        ) from exc

    return {
        "symbol": INDEX_SYMBOL,
        "resolution": INDEX_RESOLUTION,
        "date_format": "1",
        "range_from": trading_date,
        "range_to": trading_date,
        "cont_flag": "1",
    }


def fetch_index_history(
    client: Any,
    *,
    trading_date: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    if not hasattr(client, "history"):
        raise RecordedReplayError(
            "Installed FYERS client does not expose history()."
        )

    request = history_request(trading_date)
    try:
        response = client.history(data=request)
    except Exception as exc:
        raise RecordedReplayError(
            "FYERS NIFTY history request failed: "
            f"{type(exc).__name__}"
        ) from exc

    if not isinstance(response, dict):
        raise RecordedReplayError(
            "FYERS NIFTY history response was not JSON."
        )

    status = _text(response.get("s")).lower()
    candles = response.get("candles")
    if status and status != "ok":
        raise RecordedReplayError(
            "FYERS NIFTY history response failed: "
            f"code={response.get('code')} "
            f"message={_text(response.get('message') or response.get('msg'))[:200]}"
        )
    if not isinstance(candles, list) or not candles:
        raise RecordedReplayError(
            f"FYERS returned no NIFTY candles for {trading_date}."
        )

    return request, response


def normalize_index_candles(
    response: dict[str, Any],
    *,
    trading_date: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

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

        timestamp = datetime.fromtimestamp(
            epoch,
            tz=timezone.utc,
        ).astimezone().replace(tzinfo=None)

        if timestamp.date().isoformat() != trading_date:
            continue

        rows.append(
            {
                "timestamp": timestamp.isoformat(
                    sep=" ",
                    timespec="seconds",
                ),
                "open": opened,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume or 0.0,
                "source": "FYERS_NIFTY_HISTORY_5M_DATA_ONLY",
            }
        )

    deduped = {
        row["timestamp"]: row
        for row in rows
    }
    return [
        deduped[key]
        for key in sorted(deduped)
    ]


def read_option_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise RecordedReplayError(
            f"Selected CE/PE history CSV is missing: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            rows = [dict(row) for row in csv.DictReader(handle)]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise RecordedReplayError(
            "Selected CE/PE history CSV could not be read."
        ) from exc

    normalized: list[dict[str, Any]] = []
    for row in rows:
        timestamp = _parse_timestamp(row.get("timestamp"))
        side = _text(row.get("signal_side")).upper()
        if timestamp is None or side not in {"CE_BUY", "PE_BUY"}:
            continue

        close = _number(row.get("close") or row.get("ltp"))
        dte = _integer(row.get("dte"))
        if close is None or dte is None:
            continue

        normalized.append(
            {
                **row,
                "_timestamp": timestamp,
                "signal_side": side,
                "close": close,
                "ltp": close,
                "dte": dte,
            }
        )

    normalized.sort(
        key=lambda row: (
            row["_timestamp"],
            row["signal_side"],
        )
    )
    return normalized


def default_option_history(
    workspace: Path,
    trading_date: str,
) -> Path:
    return (
        workspace
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / trading_date
        / "SELECTED_OPTION_HISTORY_5M"
        / "SELECTED_CE_PE_HISTORY_5M_COMBINED.csv"
    )


def efficiency_ratio_20(
    events: list[dict[str, Any]],
) -> float | None:
    if len(events) < MIN_HISTORY_BARS:
        return None

    closes = [
        float(event["close"])
        for event in events[-MIN_HISTORY_BARS:]
    ]
    direction = abs(closes[-1] - closes[0])
    volatility = sum(
        abs(current - previous)
        for previous, current in zip(closes, closes[1:])
    )
    if volatility <= 0:
        return 0.0
    return direction / volatility


def option_index(
    rows: list[dict[str, Any]],
) -> dict[str, tuple[list[datetime], list[dict[str, Any]]]]:
    result: dict[
        str,
        tuple[list[datetime], list[dict[str, Any]]],
    ] = {}

    for side in ("CE_BUY", "PE_BUY"):
        side_rows = [
            row for row in rows
            if row["signal_side"] == side
        ]
        result[side] = (
            [row["_timestamp"] for row in side_rows],
            side_rows,
        )
    return result


def matching_option_row(
    indexed: dict[
        str,
        tuple[list[datetime], list[dict[str, Any]]],
    ],
    *,
    side: str,
    timestamp: datetime,
    max_lag_minutes: int = 5,
) -> dict[str, Any] | None:
    timestamps, rows = indexed.get(side, ([], []))
    position = bisect_right(timestamps, timestamp) - 1
    if position < 0:
        return None

    row = rows[position]
    lag = timestamp - row["_timestamp"]
    if lag < timedelta(0) or lag > timedelta(
        minutes=max_lag_minutes,
    ):
        return None
    return row


def replay_evaluations(
    index_rows: list[dict[str, Any]],
    option_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(index_rows) < MIN_HISTORY_BARS:
        raise RecordedReplayError(
            "Not enough NIFTY 5-minute bars for SMC replay. "
            f"Required={MIN_HISTORY_BARS}, actual={len(index_rows)}."
        )

    indexed_options = option_index(option_rows)
    if not indexed_options["CE_BUY"][1]:
        raise RecordedReplayError(
            "Recorded replay requires genuine CE history rows."
        )
    if not indexed_options["PE_BUY"][1]:
        raise RecordedReplayError(
            "Recorded replay requires genuine PE history rows."
        )

    events: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []

    for row in index_rows:
        timestamp = _parse_timestamp(row.get("timestamp"))
        if timestamp is None:
            continue

        event = {
            "timestamp": row["timestamp"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row.get("volume") or 0.0),
        }
        events.append(event)

        if len(events) < MIN_HISTORY_BARS:
            continue

        decision, reason, close_change = _run_gate(events)
        decision = _text(decision).upper()
        side = map_decision(decision)
        er20 = efficiency_ratio_20(events)

        option_row = (
            matching_option_row(
                indexed_options,
                side=side,
                timestamp=timestamp,
            )
            if side in {"CE_BUY", "PE_BUY"}
            else None
        )

        option_ltp = (
            float(option_row["ltp"])
            if option_row is not None
            else None
        )
        dte = (
            int(option_row["dte"])
            if option_row is not None
            else None
        )

        er20_ok = er20 is not None and er20 >= MIN_ER20
        premium_ok = (
            option_ltp is not None
            and MIN_PREMIUM <= option_ltp <= MAX_PREMIUM
        )
        dte_ok = dte is not None and dte >= MIN_DTE
        option_ready = option_row is not None

        signal_generated = bool(
            side in {"CE_BUY", "PE_BUY"}
            and er20_ok
            and option_ready
            and premium_ok
            and dte_ok
        )

        rejection_reasons: list[str] = []
        if side == "NO_TRADE":
            rejection_reasons.append("SMC_NEUTRAL")
        if not er20_ok:
            rejection_reasons.append("ER20_BELOW_0.30")
        if side in {"CE_BUY", "PE_BUY"} and not option_ready:
            rejection_reasons.append(
                f"{side}_MATCHING_5M_CANDLE_MISSING"
            )
        if option_ready and not dte_ok:
            rejection_reasons.append("DTE_BELOW_1")
        if option_ready and not premium_ok:
            rejection_reasons.append(
                "OPTION_PREMIUM_OUTSIDE_20_200"
            )

        evaluations.append(
            {
                "timestamp": row["timestamp"],
                "smc_decision": decision,
                "signal_side": side,
                "signal_generated": signal_generated,
                "smc_reason": reason,
                "close_change": close_change,
                "er20": (
                    round(er20, 6)
                    if er20 is not None
                    else None
                ),
                "option_symbol": (
                    _text(option_row.get("symbol"))
                    if option_row is not None
                    else ""
                ),
                "option_ltp": option_ltp,
                "dte": dte,
                "rejection_reason": (
                    ";".join(rejection_reasons)
                    if rejection_reasons
                    else "ALL_REPLAY_GATES_PASSED"
                ),
                "data_mode": "RECORDED_FYERS_DATA_REPLAY",
                "paper_only": True,
                "evaluation_only": True,
                "position_opened": False,
                "pnl_calculated": False,
                "real_orders_allowed": False,
                "broker_execution_allowed": False,
                "auto_trading_allowed": False,
            }
        )

    if not evaluations:
        raise RecordedReplayError(
            "No replay evaluations were produced."
        )
    return evaluations


def summary_payload(
    *,
    trading_date: str,
    index_request: dict[str, Any],
    index_rows: list[dict[str, Any]],
    option_history_csv: Path,
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    decision_counts = Counter(
        row["smc_decision"]
        for row in evaluations
    )
    side_counts = Counter(
        row["signal_side"]
        for row in evaluations
    )
    accepted = [
        row for row in evaluations
        if row["signal_generated"]
    ]
    accepted_side_counts = Counter(
        row["signal_side"]
        for row in accepted
    )

    first_accepted = accepted[0] if accepted else None
    last_evaluation = evaluations[-1]

    return {
        "version": MODULE_VERSION,
        "status": "RECORDED_DATA_REPLAY_EVALUATED",
        "day_label": f"RECORDED_REPLAY_{trading_date}",
        "trading_date": trading_date,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),
        "workflow": "CURRENT_DAY_RECORDED_FYERS_DATA_REPLAY",
        "strategy": (
            "SMC_BIDIRECTIONAL_LONG_CE_SHORT_PE_NEUTRAL_NO_TRADE"
        ),
        "locked_candidate": (
            "SMC_BIDIRECTIONAL_ER20_GE_030_LONG_CE_SHORT_PE_"
            "DTE_GE_1_LTP_20_200_RECORDED_REPLAY_EVALUATION"
        ),
        "index_request": index_request,
        "index_rows": len(index_rows),
        "option_history_csv": str(option_history_csv),
        "evaluation_count": len(evaluations),
        "decision_counts": dict(decision_counts),
        "side_counts": dict(side_counts),
        "accepted_evaluation_count": len(accepted),
        "accepted_side_counts": dict(accepted_side_counts),
        "first_accepted_evaluation": first_accepted or {},
        "last_evaluation": last_evaluation,
        "signal_generated": bool(accepted),
        "event": (
            "RECORDED_DATA_SIGNAL_EVALUATION_FOUND"
            if accepted
            else "RECORDED_DATA_NO_ACCEPTED_SIGNAL"
        ),
        "action": (
            "REVIEW_RECORDED_SIGNAL_EVIDENCE"
            if accepted
            else "HOLD_NO_RECORDED_SIGNAL"
        ),
        "gate": "RECORDED_DATA_REPLAY_EVALUATION_ONLY",
        "position_state": "NO_POSITION_EVALUATION_ONLY",
        "entry": "",
        "stop_loss": "",
        "target": "",
        "exit_reason": "",
        "paper_pnl": 0.0,
        "replay_truth": {
            "genuine_fyers_index_history": True,
            "genuine_fyers_ce_history": True,
            "genuine_fyers_pe_history": True,
            "paper_trade_created": False,
            "position_opened": False,
            "pnl_calculated": False,
            "historical_execution_claim": False,
        },
        "paper_only": True,
        "data_only": True,
        "recorded_data_replay": True,
        "evaluation_only": True,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "profitability_claim": False,
        "safety_lock": REPLAY_SAFETY,
        "next_required_step": (
            "REVIEW_REPLAY_REPORT_THEN_INTEGRATE_WITH_TODAY_REPORT"
        ),
    }


def output_paths(
    workspace: Path,
    trading_date: str,
) -> dict[str, Path]:
    folder = (
        workspace
        / "HQE_CURRENT_DAY_RECORDED_REPLAY"
        / trading_date
    )
    return {
        "folder": folder,
        "index_csv": folder / "NIFTY_INDEX_HISTORY_5M.csv",
        "evaluations_csv": (
            folder / "SMC_RECORDED_REPLAY_EVALUATIONS.csv"
        ),
        "summary_json": (
            folder / "HQE_CURRENT_DAY_RECORDED_REPLAY_SUMMARY.json"
        ),
        "report_html": (
            folder / "HQE_CURRENT_DAY_RECORDED_REPLAY_REPORT.html"
        ),
        "status_json": (
            workspace / "HQE_CURRENT_DAY_RECORDED_REPLAY_STATUS.json"
        ),
    }


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


def _atomic_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        raise RecordedReplayError(
            f"Refusing to write empty CSV: {path.name}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())

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
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    temporary.replace(path)


def render_html(summary: dict[str, Any]) -> str:
    counts = summary["decision_counts"]
    accepted = summary["accepted_side_counts"]
    first = summary["first_accepted_evaluation"]
    last = summary["last_evaluation"]

    def safe(value: Any) -> str:
        return html.escape(_text(value) or "—")

    accepted_message = (
        (
            f"First accepted replay evaluation: "
            f"{safe(first.get('timestamp'))} · "
            f"{safe(first.get('signal_side'))} · "
            f"premium ₹{safe(first.get('option_ltp'))}"
        )
        if first
        else (
            "No recorded bar passed every SMC, ER20, DTE and "
            "premium gate."
        )
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HQE Recorded Data Replay — {safe(summary['trading_date'])}</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f4f7fb; color: #172033; }}
main {{ max-width: 1060px; margin: 28px auto; padding: 0 18px 36px; }}
header {{ background: linear-gradient(135deg, #101d3b, #243d72); color: white; padding: 28px; border-radius: 18px; }}
.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 18px; }}
.card {{ background: white; border-radius: 14px; padding: 18px; box-shadow: 0 8px 24px rgba(20,40,80,.08); }}
.wide {{ grid-column: 1 / -1; }}
.label {{ color: #667085; font-size: 13px; }}
.value {{ font-size: 24px; font-weight: 700; margin-top: 6px; }}
.notice {{ border-left: 5px solid #d69e2e; }}
.pass {{ border-left: 5px solid #228b5a; }}
code {{ word-break: break-all; }}
@media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} .wide {{ grid-column: auto; }} }}
</style>
</head>
<body>
<main>
<header>
<h1>HQE Current-Day Recorded Data Replay</h1>
<p>{safe(summary['trading_date'])} · Genuine FYERS index + CE + PE history</p>
</header>
<section class="grid">
<div class="card"><div class="label">Replay evaluations</div><div class="value">{summary['evaluation_count']}</div></div>
<div class="card"><div class="label">Accepted evaluations</div><div class="value">{summary['accepted_evaluation_count']}</div></div>
<div class="card"><div class="label">Data mode</div><div class="value" style="font-size:18px">Recorded replay</div></div>
<div class="card"><div class="label">LONG decisions</div><div class="value">{counts.get('LONG', 0)}</div></div>
<div class="card"><div class="label">SHORT decisions</div><div class="value">{counts.get('SHORT', 0)}</div></div>
<div class="card"><div class="label">NEUTRAL decisions</div><div class="value">{counts.get('NEUTRAL', 0)}</div></div>
<div class="card pass wide">
<h2>Direction truth</h2>
<p>LONG → CE BUY evaluation · SHORT → PE BUY evaluation · NEUTRAL → no trade.</p>
<p>{accepted_message}</p>
<p>Accepted CE evaluations: {accepted.get('CE_BUY', 0)} · Accepted PE evaluations: {accepted.get('PE_BUY', 0)}</p>
</div>
<div class="card wide">
<h2>Last recorded evaluation</h2>
<p><strong>Time:</strong> {safe(last.get('timestamp'))}</p>
<p><strong>SMC decision:</strong> {safe(last.get('smc_decision'))}</p>
<p><strong>Mapped side:</strong> {safe(last.get('signal_side'))}</p>
<p><strong>ER20:</strong> {safe(last.get('er20'))}</p>
<p><strong>Reason:</strong> {safe(last.get('rejection_reason'))}</p>
</div>
<div class="card notice wide">
<h2>Safety and interpretation</h2>
<p>This report evaluates genuine recorded market data. It does not claim that a historical trade was executed.</p>
<p>No position was opened, no P&amp;L was calculated, and no broker/order API was used.</p>
<p>Real orders, broker execution, auto trading and option selling remain blocked.</p>
</div>
<div class="card wide">
<h2>Evidence</h2>
<p><strong>Option history:</strong> <code>{safe(summary['option_history_csv'])}</code></p>
<p><strong>Strategy:</strong> {safe(summary['strategy'])}</p>
</div>
</section>
</main>
</body>
</html>
"""


def run_live_data_only(
    *,
    workspace: Path,
    trading_date: str,
    option_history_csv: Path | None = None,
    client: Any | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not workspace.exists():
        raise RecordedReplayError(
            f"Workspace does not exist: {workspace}"
        )

    option_path = option_history_csv or default_option_history(
        workspace,
        trading_date,
    )
    option_rows = read_option_history(option_path)

    if client is None:
        environment = env if env is not None else __import__("os").environ
        client = build_fyers_client(
            client_id=environment.get("FYERS_CLIENT_ID", ""),
            access_token=environment.get("FYERS_ACCESS_TOKEN", ""),
        )

    request, response = fetch_index_history(
        client,
        trading_date=trading_date,
    )
    index_rows = normalize_index_candles(
        response,
        trading_date=trading_date,
    )

    if len(index_rows) < MIN_HISTORY_BARS:
        raise RecordedReplayError(
            "FYERS NIFTY history did not contain enough valid "
            f"5-minute rows. Actual={len(index_rows)}."
        )

    evaluations = replay_evaluations(
        index_rows,
        option_rows,
    )
    summary = summary_payload(
        trading_date=trading_date,
        index_request=request,
        index_rows=index_rows,
        option_history_csv=option_path,
        evaluations=evaluations,
    )
    paths = output_paths(workspace, trading_date)

    _atomic_csv(paths["index_csv"], index_rows)
    _atomic_csv(paths["evaluations_csv"], evaluations)
    _atomic_json(paths["summary_json"], summary)

    paths["report_html"].parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    paths["report_html"].write_text(
        render_html(summary),
        encoding="utf-8",
    )

    result = {
        **summary,
        "outputs": {
            "index_csv": str(paths["index_csv"]),
            "evaluations_csv": str(paths["evaluations_csv"]),
            "summary_json": str(paths["summary_json"]),
            "report_html": str(paths["report_html"]),
        },
    }
    _atomic_json(paths["status_json"], result)
    return result


def guard_payload() -> dict[str, Any]:
    return {
        "version": MODULE_VERSION,
        "guard_check_status": "PASS",
        "workflow": "CURRENT_DAY_RECORDED_DATA_REPLAY_EVALUATION",
        "live_api_call_performed": False,
        "paper_trade_created": False,
        "position_opened": False,
        "pnl_calculated": False,
        "order_api_available_to_module": False,
        "real_orders_allowed": False,
        "broker_execution_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "safety_lock": REPLAY_SAFETY,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate current-day genuine FYERS index and CE/PE "
            "recorded data through the bidirectional SMC gate."
        )
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--trading-date", default="")
    parser.add_argument("--option-history-csv", type=Path)
    parser.add_argument(
        "--evaluate-live-data-only",
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

    if not args.evaluate_live_data_only:
        parser.error(
            "Use --guard-check or explicitly pass "
            "--evaluate-live-data-only."
        )
    if args.workspace is None:
        parser.error("--workspace is required.")
    if not args.trading_date:
        parser.error("--trading-date is required.")

    try:
        payload = run_live_data_only(
            workspace=args.workspace,
            trading_date=args.trading_date,
            option_history_csv=args.option_history_csv,
        )
    except RecordedReplayError as exc:
        print(
            json.dumps(
                {
                    "version": MODULE_VERSION,
                    "status": "FAILED_SAFE",
                    "error": str(exc),
                    "paper_only": True,
                    "data_only": True,
                    "recorded_data_replay": True,
                    "evaluation_only": True,
                    "paper_trade_created": False,
                    "position_opened": False,
                    "pnl_calculated": False,
                    "real_orders_allowed": False,
                    "broker_execution_allowed": False,
                    "auto_trading_allowed": False,
                    "option_selling_allowed": False,
                    "safety_lock": REPLAY_SAFETY,
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
