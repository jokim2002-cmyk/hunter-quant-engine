from __future__ import annotations

import csv
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO
    / "scripts"
    / "hqe_current_day_recorded_replay_evaluation.py"
)
IST = ZoneInfo("Asia/Kolkata")


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hqe_current_day_recorded_replay_evaluation",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def epoch_ist(value: str) -> int:
    parsed = datetime.fromisoformat(value).replace(tzinfo=IST)
    return int(parsed.timestamp())


def index_response(count: int = 30):
    candles = []
    for number in range(count):
        minute = 15 + number * 5
        hour = 9 + minute // 60
        minute = minute % 60
        timestamp = (
            f"2026-07-13 {hour:02d}:{minute:02d}:00"
        )
        base = 24000 + number * 5
        candles.append(
            [
                epoch_ist(timestamp),
                base,
                base + 12,
                base - 8,
                base + 4,
                1000 + number,
            ]
        )
    return {"s": "ok", "code": 200, "candles": candles}


def option_rows(count: int = 30):
    rows = []
    for number in range(count):
        minute = 15 + number * 5
        hour = 9 + minute // 60
        minute = minute % 60
        timestamp = (
            f"2026-07-13 {hour:02d}:{minute:02d}:00"
        )
        rows.extend(
            [
                {
                    "timestamp": timestamp,
                    "symbol": "NSE:NIFTY_TEST_CE",
                    "signal_side": "CE_BUY",
                    "strike_price": "24200",
                    "expiry_timestamp": "2026-07-14",
                    "dte": "1",
                    "open": "100",
                    "high": "110",
                    "low": "95",
                    "close": "105",
                    "ltp": "105",
                    "volume": "1000",
                },
                {
                    "timestamp": timestamp,
                    "symbol": "NSE:NIFTY_TEST_PE",
                    "signal_side": "PE_BUY",
                    "strike_price": "24200",
                    "expiry_timestamp": "2026-07-14",
                    "dte": "1",
                    "open": "90",
                    "high": "98",
                    "low": "85",
                    "close": "92",
                    "ltp": "92",
                    "volume": "1200",
                },
            ]
        )
    return rows


def write_options(path: Path) -> None:
    rows = option_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)


class FakeClient:
    def __init__(self):
        self.calls = []

    def history(self, *, data):
        self.calls.append(dict(data))
        return index_response()


def test_guard_check_blocks_execution_and_pnl():
    module = load_module()
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["paper_trade_created"] is False
    assert payload["position_opened"] is False
    assert payload["pnl_calculated"] is False
    assert payload["order_api_available_to_module"] is False


def test_efficiency_ratio_is_bounded():
    module = load_module()
    events = [
        {"close": float(100 + number)}
        for number in range(21)
    ]
    value = module.efficiency_ratio_20(events)
    assert value == 1.0


def test_replay_maps_long_to_ce_and_neutral_to_no_trade(
    monkeypatch,
):
    module = load_module()
    index_rows = module.normalize_index_candles(
        index_response(),
        trading_date="2026-07-13",
    )
    options = []
    for row in option_rows():
        parsed = dict(row)
        parsed["_timestamp"] = module._parse_timestamp(
            row["timestamp"]
        )
        parsed["close"] = float(row["close"])
        parsed["ltp"] = float(row["ltp"])
        parsed["dte"] = int(row["dte"])
        options.append(parsed)

    decisions = iter(
        [
            ("LONG", "bullish_smc", 100.0),
            ("NEUTRAL", "no_confluence", 0.0),
        ]
        + [("LONG", "bullish_smc", 100.0)] * 20
    )
    monkeypatch.setattr(
        module,
        "_run_gate",
        lambda events: next(decisions),
    )
    monkeypatch.setattr(
        module,
        "efficiency_ratio_20",
        lambda events: 0.50,
    )

    evaluations = module.replay_evaluations(
        index_rows,
        options,
    )
    assert evaluations[0]["signal_side"] == "CE_BUY"
    assert evaluations[0]["signal_generated"] is True
    assert evaluations[1]["signal_side"] == "NO_TRADE"
    assert evaluations[1]["signal_generated"] is False


def test_live_data_only_writes_truthful_evidence(
    tmp_path,
    monkeypatch,
):
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    option_path = module.default_option_history(
        workspace,
        "2026-07-13",
    )
    write_options(option_path)

    monkeypatch.setattr(
        module,
        "_run_gate",
        lambda events: ("LONG", "bullish_smc", 100.0),
    )
    monkeypatch.setattr(
        module,
        "efficiency_ratio_20",
        lambda events: 0.50,
    )

    client = FakeClient()
    payload = module.run_live_data_only(
        workspace=workspace,
        trading_date="2026-07-13",
        client=client,
        env={},
    )

    assert payload["status"] == (
        "RECORDED_DATA_REPLAY_EVALUATED"
    )
    assert payload["signal_generated"] is True
    assert payload["accepted_side_counts"]["CE_BUY"] > 0
    assert payload["replay_truth"]["paper_trade_created"] is False
    assert payload["replay_truth"]["position_opened"] is False
    assert payload["replay_truth"]["pnl_calculated"] is False
    assert payload["paper_pnl"] == 0.0
    assert len(client.calls) == 1

    outputs = payload["outputs"]
    assert Path(outputs["index_csv"]).exists()
    assert Path(outputs["evaluations_csv"]).exists()
    assert Path(outputs["summary_json"]).exists()
    assert Path(outputs["report_html"]).exists()


def test_source_has_no_order_or_position_execution_calls():
    text = SCRIPT.read_text(encoding="utf-8-sig")
    forbidden = (
        ".place_order(",
        ".submit_order(",
        ".modify_order(",
        ".cancel_order(",
        ".exit_positions(",
        "POSITION_OPENED",
    )
    assert not any(marker in text for marker in forbidden)
    assert ".history(" in text
    assert "evaluation_only" in text
