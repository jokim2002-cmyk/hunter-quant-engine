import csv
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_30_valid_trade_day_tracker.py"
spec = importlib.util.spec_from_file_location("hqe_30_valid_trade_day_tracker", MODULE_PATH)
tracker = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(tracker)


def write_csv(path: Path, headers, rows, encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_zero_trade_day_is_observed_but_not_valid(tmp_path):
    write_csv(
        tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["date", "day_number", "trade_count", "safety_ok", "candidate_tuning", "manual_override"],
        [
            {
                "date": "2026-07-09",
                "day_number": "1",
                "trade_count": "0",
                "safety_ok": "YES",
                "candidate_tuning": "NO",
                "manual_override": "NO",
            }
        ],
        encoding="utf-8-sig",
    )

    payload = tracker.evaluate_workspace(tmp_path)

    assert payload["tracker_status"] == "PASS"
    assert payload["observed_session_days"] == 1
    assert payload["valid_paper_trade_days"] == 0
    assert payload["no_trade_observed_days"] == 1
    assert payload["actual_paper_trades"] == 0
    assert payload["remaining_valid_trade_days"] == 30
    assert payload["decision"] == "HOLD_MORE_VALID_TRADE_DAYS_REQUIRED"
    assert payload["real_money_automatic"] is False
    assert payload["fake_trades_created"] is False


def test_no_trade_days_do_not_count_toward_target(tmp_path):
    write_csv(
        tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["trading_date", "trade_count", "safety_ok"],
        [
            {"trading_date": "2026-07-09", "trade_count": "0", "safety_ok": "YES"},
            {"trading_date": "2026-07-10", "trade_count": "1", "safety_ok": "YES"},
            {"trading_date": "2026-07-13", "trade_count": "0", "safety_ok": "YES"},
        ],
    )
    write_csv(
        tmp_path / "DAY_002_FORWARD_TRADE_LOG.csv",
        ["trading_date", "symbol", "expiry_date", "net_pnl"],
        [{"trading_date": "2026-07-10", "symbol": "NIFTY_PE", "expiry_date": "2026-07-16", "net_pnl": "125"}],
    )

    payload = tracker.evaluate_workspace(tmp_path)

    assert payload["observed_session_days"] == 3
    assert payload["valid_paper_trade_days"] == 1
    assert payload["no_trade_observed_days"] == 2
    assert payload["actual_paper_trades"] == 1
    assert payload["remaining_valid_trade_days"] == 29
    assert payload["valid_trade_dates"] == ["2026-07-10"]


def test_valid_days_require_actual_trade_rows_not_only_ledger_count(tmp_path):
    write_csv(
        tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["trading_date", "trade_count", "safety_ok"],
        [
            {"trading_date": "2026-07-10", "trade_count": "1", "safety_ok": "YES"},
            {"trading_date": "2026-07-11", "trade_count": "1", "safety_ok": "YES"},
        ],
    )
    write_csv(
        tmp_path / "FORWARD_VALIDATION_MASTER_LEDGER.csv",
        ["entry_time", "symbol", "expiry", "net"],
        [{"entry_time": "2026-07-10T10:00:00", "symbol": "NIFTY_PE", "expiry": "2026-07-16", "net": "50"}],
    )

    payload = tracker.evaluate_workspace(tmp_path)

    assert payload["day_ledger_positive_trade_days"] == 2
    assert payload["actual_paper_trades"] == 1
    assert payload["valid_paper_trade_days"] == 1
    assert "DAY_LEDGER_POSITIVE_WITHOUT_ACTUAL_TRADE_ROWS:2026-07-11" in payload["warnings"]


def test_expiry_weeks_come_only_from_actual_trade_rows(tmp_path):
    write_csv(
        tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["trading_date", "trade_count", "safety_ok"],
        [
            {"trading_date": "2026-07-10", "trade_count": "1", "safety_ok": "YES"},
            {"trading_date": "2026-07-20", "trade_count": "1", "safety_ok": "YES"},
        ],
    )
    write_csv(
        tmp_path / "DAY_010_FORWARD_TRADE_LOG.csv",
        ["datetime", "symbol", "expiry_date", "net_pnl"],
        [
            {"datetime": "2026-07-10T10:15:00", "symbol": "NIFTY_PE", "expiry_date": "2026-07-16", "net_pnl": "100"},
            {"datetime": "2026-07-20T11:15:00", "symbol": "NIFTY_PE", "expiry_date": "2026-07-23", "net_pnl": "200"},
        ],
    )

    payload = tracker.evaluate_workspace(tmp_path)

    assert payload["distinct_expiry_weeks"] == 2
    assert payload["expiry_weeks"] == ["2026-W29", "2026-W30"]
    assert payload["cumulative_forward_net"] == 300.0


def test_write_outputs_and_guard_check(tmp_path):
    write_csv(
        tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["date", "trade_count"],
        [{"date": "2026-07-09", "trade_count": "0"}],
    )

    payload = tracker.evaluate_workspace(tmp_path, write=True)
    guard = tracker.guard_check()

    assert (tmp_path / "FORWARD_VALIDATION_30_VALID_TRADE_DAY_TRACKER.json").exists()
    assert (tmp_path / "FORWARD_VALIDATION_30_VALID_TRADE_DAY_TRACKER.md").exists()
    assert (tmp_path / "FORWARD_VALIDATION_30_VALID_TRADE_DAY_TRACKER_LEDGER.csv").exists()
    assert payload["safety_lock"]["paper_only"] is True
    assert guard["guard_check_status"] == "PASS"
    assert guard["order_api_invoked"] is False
    assert guard["broker_execution_invoked"] is False
    assert guard["external_api_calls_executed"] is False
