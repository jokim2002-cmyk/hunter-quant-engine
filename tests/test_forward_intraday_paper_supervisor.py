import csv
import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_forward_intraday_paper_supervisor.py"
SPEC = importlib.util.spec_from_file_location("run_forward_intraday_paper_supervisor", SCRIPT_PATH)
supervisor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = supervisor
SPEC.loader.exec_module(supervisor)


def write_index_csv(path: Path, *, falling: bool = True, end_price: float = 22000.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 7, 9, 9, 15)
    rows = []
    for index in range(21):
        dt = start + timedelta(minutes=5 * index)
        if falling:
            close = end_price + (20 - index) * 10
        else:
            close = end_price - (20 - index) * 2
        rows.append(
            {
                "datetime": dt.isoformat(timespec="minutes"),
                "open": close + 1,
                "high": close + 5,
                "low": close - 5,
                "close": close,
                "volume": 1000,
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["datetime", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(rows)


def write_premium_csv(path: Path, *, ltp: float = 100.0, high: float = 105.0, low: float = 95.0, dte: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dt = datetime(2026, 7, 9, 10, 55)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["datetime", "open", "high", "low", "close", "last_traded_price", "dte"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "datetime": dt.isoformat(timespec="minutes"),
                "open": ltp,
                "high": high,
                "low": low,
                "close": ltp,
                "last_traded_price": ltp,
                "dte": dte,
            }
        )


def paths(tmp_path: Path) -> supervisor.SupervisorPaths:
    return supervisor.SupervisorPaths(
        index_csv=tmp_path / "index.csv",
        premium_csv=tmp_path / "premium.csv",
        out_dir=tmp_path / "out",
        state_json=tmp_path / "out" / "state.json",
        ledger_csv=tmp_path / "out" / "ledger.csv",
    )


def test_safety_contract_blocks_real_execution_flags():
    assert supervisor.PAPER_ONLY is True
    assert supervisor.REAL_MONEY_ALLOWED is False
    assert supervisor.BROKER_EXECUTION_ALLOWED is False
    assert supervisor.REAL_ORDERS_ALLOWED is False
    assert supervisor.AUTO_TRADING_ALLOWED is False
    assert supervisor.OPTION_SELLING_ALLOWED is False
    supervisor.assert_safety_contract()


def test_not_ready_when_premium_data_missing(tmp_path):
    p = paths(tmp_path)
    write_index_csv(p.index_csv)
    summary = supervisor.run_one_cycle(p, datetime(2026, 7, 9, 10, 55))
    assert summary["data_ready"] is False
    assert summary["signal_generated"] is False
    assert summary["readiness_reason"] == "PREMIUM_DATA_NOT_READY"
    assert Path(summary["report"]).exists()


def test_locked_candidate_opens_pe_paper_position(tmp_path):
    p = paths(tmp_path)
    write_index_csv(p.index_csv, falling=True)
    write_premium_csv(p.premium_csv, ltp=100.0, dte=2)
    summary = supervisor.run_one_cycle(p, datetime(2026, 7, 9, 10, 55))
    assert summary["data_ready"] is True
    assert summary["signal_generated"] is True
    assert summary["event"] == "POSITION_OPENED"
    assert summary["entry"] == 100.0
    assert summary["stop_loss"] == 60.0
    assert summary["target"] == 220.0
    state = json.loads(p.state_json.read_text(encoding="utf-8"))
    assert state["status"] == "OPEN"
    assert state["side"] == "PE_BUY"
    assert state["broker_execution_allowed"] is False


def test_locked_candidate_rejects_non_falling_index(tmp_path):
    p = paths(tmp_path)
    write_index_csv(p.index_csv, falling=False)
    write_premium_csv(p.premium_csv, ltp=100.0, dte=2)
    summary = supervisor.run_one_cycle(p, datetime(2026, 7, 9, 10, 55))
    assert summary["data_ready"] is True
    assert summary["signal_generated"] is False
    assert "PE_REJECT_INDEX_NOT_FALLING" in summary["pe_reason"]
    state = json.loads(p.state_json.read_text(encoding="utf-8"))
    assert state["status"] == "FLAT"


def test_open_position_closes_on_target_paper_only(tmp_path):
    p = paths(tmp_path)
    write_index_csv(p.index_csv, falling=True)
    write_premium_csv(p.premium_csv, ltp=100.0, high=105.0, low=95.0, dte=2)
    first = supervisor.run_one_cycle(p, datetime(2026, 7, 9, 10, 55))
    assert first["event"] == "POSITION_OPENED"

    write_premium_csv(p.premium_csv, ltp=220.0, high=225.0, low=210.0, dte=2)
    second = supervisor.run_one_cycle(p, datetime(2026, 7, 9, 11, 0))
    assert second["event"] == "POSITION_CLOSED"
    assert second["exit_reason"] == "TARGET_HIT_PAPER_ONLY"
    assert second["paper_pnl"] == 120.0
    state = json.loads(p.state_json.read_text(encoding="utf-8"))
    assert state["status"] == "FLAT"
