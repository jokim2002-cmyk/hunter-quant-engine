from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
MODULE_PATH = SCRIPTS / "hqe_paper_product_runtime.py"


def load_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "hqe_paper_product_runtime_test",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_guard_payload_preserves_all_execution_locks():
    module = load_module()
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["canonical_runtime"] is True
    assert payload["paper_only"] is True
    assert payload["real_orders_allowed"] is False
    assert payload["broker_execution_allowed"] is False
    assert payload["auto_trading_allowed"] is False
    assert payload["real_money_allowed"] is False


def test_discover_inputs_uses_exact_trading_date(tmp_path):
    module = load_module()
    trading_date = datetime(2026, 7, 15, 13, 0)
    index = (
        tmp_path
        / "HQE_CURRENT_DAY_RECORDED_REPLAY"
        / "2026-07-15"
        / module.INDEX_FILENAME
    )
    premium = (
        tmp_path
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / "2026-07-15"
        / "SELECTED_OPTION_HISTORY_5M"
        / module.PREMIUM_FILENAME
    )
    index.parent.mkdir(parents=True)
    premium.parent.mkdir(parents=True)
    index.write_text("datetime,close\n2026-07-15T12:55:00,25000\n", encoding="utf-8")
    premium.write_text("datetime,close\n2026-07-15T12:55:00,100\n", encoding="utf-8")

    found_index, found_premium = module.discover_inputs(tmp_path, trading_date)

    assert found_index == index
    assert found_premium == premium


def test_open_position_snapshot_calculates_latest_price_and_unrealized_pnl(
    monkeypatch,
    tmp_path,
):
    module = load_module()
    monkeypatch.setattr(module, "runtime_process_alive", lambda pid, workspace=None: False)
    paths = module.runtime_paths(tmp_path)
    paths["folder"].mkdir(parents=True)

    premium = (
        tmp_path
        / "HQE_CURRENT_DAY_OPTION_DATA"
        / "2026-07-15"
        / "SELECTED_OPTION_HISTORY_5M"
        / module.PREMIUM_FILENAME
    )
    write_csv(
        premium,
        [
            {
                "datetime": "2026-07-15T12:55:00",
                "signal_side": "CE_BUY",
                "symbol": "NSE:TESTCE",
                "close": 100.0,
            },
            {
                "datetime": "2026-07-15T13:00:00",
                "signal_side": "CE_BUY",
                "symbol": "NSE:TESTCE",
                "close": 112.5,
            },
        ],
    )

    module.write_json(
        paths["state"],
        {
            "status": "OPEN",
            "side": "CE_BUY",
            "option_symbol": "NSE:TESTCE",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "quantity": 2,
            "entry_time": "2026-07-15T12:55:00",
        },
    )
    module.write_json(
        paths["summary"],
        {
            "data_ready": True,
            "position_state": "OPEN",
            "event": "POSITION_HELD",
        },
    )
    module.write_json(
        paths["runtime"],
        {
            "pid": 0,
            "status": "STOPPED_BY_OPERATOR",
            "last_premium_csv": str(premium),
        },
    )

    snapshot = module.paper_product_snapshot(
        tmp_path,
        datetime(2026, 7, 15, 13, 1),
    )

    assert snapshot["position_status"] == "OPEN"
    assert snapshot["latest_option_price"] == 112.5
    assert snapshot["latest_option_price_time"] == "2026-07-15T13:00:00"
    assert snapshot["unrealized_paper_pnl"] == 25.0
    assert snapshot["real_orders_allowed"] is False


def test_closed_position_snapshot_reads_realized_pnl_from_ledger(
    monkeypatch,
    tmp_path,
):
    module = load_module()
    monkeypatch.setattr(module, "runtime_process_alive", lambda pid, workspace=None: False)
    paths = module.runtime_paths(tmp_path)
    paths["folder"].mkdir(parents=True)

    module.write_json(
        paths["state"],
        {
            "status": "CLOSED",
            "side": "PE_BUY",
            "option_symbol": "NSE:TESTPE",
            "entry": 179.0,
        },
    )
    write_csv(
        paths["ledger"],
        [
            {
                "timestamp": "2026-07-15T12:55:00",
                "module": "MODULE_131",
                "event": "POSITION_OPENED",
                "side": "PE_BUY",
                "option_symbol": "NSE:TESTPE",
                "entry": 179.0,
                "stop_loss": 107.4,
                "target": 393.8,
                "exit_reason": "",
                "paper_pnl": 0.0,
                "paper_only": True,
            },
            {
                "timestamp": "2026-07-15T15:25:00",
                "module": "MODULE_131",
                "event": "POSITION_CLOSED",
                "side": "PE_BUY",
                "option_symbol": "NSE:TESTPE",
                "entry": 179.0,
                "stop_loss": 107.4,
                "target": 393.8,
                "exit_reason": "EOD_EXIT_PAPER_ONLY",
                "paper_pnl": -28.95,
                "paper_only": True,
            },
        ],
    )

    snapshot = module.paper_product_snapshot(
        tmp_path,
        datetime(2026, 7, 15, 15, 26),
    )

    assert snapshot["position_status"] == "CLOSED"
    assert snapshot["realized_paper_pnl"] == -28.95
    assert snapshot["exit_reason"] == "EOD_EXIT_PAPER_ONLY"
    assert snapshot["today_completed_trades"] == 1
