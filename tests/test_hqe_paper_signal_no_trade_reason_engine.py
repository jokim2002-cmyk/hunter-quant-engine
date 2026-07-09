from __future__ import annotations

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import hqe_paper_signal_no_trade_reason_engine as engine


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()}) if rows else ["decision", "reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_missing_signal_feed_records_no_trade_reason_without_fake_trade(tmp_path):
    payload = engine.evaluate_paper_signal_no_trade_reason(
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
        write=True,
    )

    assert payload["engine_status"] == "PASS"
    assert payload["engine_decision"] == "NO_TRADE_REASON_RECORDED"
    assert payload["no_trade_reason"] == "MISSING_SIGNAL_FEED"
    assert payload["actual_paper_trades"] == 0
    assert payload["fake_trades_created"] is False
    assert payload["order_api_invoked"] is False
    assert payload["external_api_calls_executed"] is False
    assert payload["candidate_tuning"] is False
    assert (tmp_path / "DAY_001_PAPER_SIGNAL_NO_TRADE_REASON.json").exists()
    assert (tmp_path / "DAY_001_PAPER_SIGNAL_NO_TRADE_REASON.md").exists()
    assert (tmp_path / "PAPER_SIGNAL_NO_TRADE_REASON_LEDGER.csv").exists()


def test_rejected_signal_feed_uses_top_rejection_reason(tmp_path):
    feed = tmp_path / "DAY_001_FORWARD_SIGNAL_FEED.csv"
    write_csv(
        feed,
        [
            {"decision": "REJECTED", "rejection_reason": "ER20 below locked threshold"},
            {"decision": "REJECTED", "rejection_reason": "ER20 below locked threshold"},
            {"decision": "BLOCKED", "blocked_reason": "LTP outside 20-200"},
        ],
    )

    payload = engine.evaluate_paper_signal_no_trade_reason(
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
    )

    assert payload["signal_feed_rows"] == 3
    assert payload["approved_signal_rows"] == 0
    assert payload["rejected_signal_rows"] == 3
    assert payload["engine_decision"] == "NO_TRADE_REASON_RECORDED"
    assert payload["no_trade_reason"] == "ER20 below locked threshold"
    assert payload["reason_counts"]["ER20 below locked threshold"] == 2
    assert payload["locked_validation_candidate_unchanged"] is True


def test_approved_signal_does_not_create_fake_trade(tmp_path):
    feed = tmp_path / "DAY_001_FORWARD_SIGNAL_FEED.csv"
    write_csv(
        feed,
        [
            {
                "paper_signal_decision": "PAPER_SIGNAL_APPROVED",
                "symbol": "NSE:NIFTY50-INDEX",
                "option_type": "PE",
            }
        ],
    )

    payload = engine.evaluate_paper_signal_no_trade_reason(
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
    )

    assert payload["approved_signal_rows"] == 1
    assert payload["actual_paper_trades"] == 0
    assert payload["engine_decision"] == "PAPER_SIGNAL_PRESENT_AWAITING_ACTUAL_PAPER_TRADE_ROW"
    assert payload["no_trade_reason"] == "APPROVED_PAPER_SIGNAL_PRESENT_BUT_NO_ACTUAL_PAPER_TRADE_ROW"
    assert payload["fake_trades_created"] is False
    assert payload["broker_execution_invoked"] is False


def test_actual_paper_trade_rows_are_counted_from_trade_log_only(tmp_path):
    feed = tmp_path / "DAY_001_FORWARD_SIGNAL_FEED.csv"
    trade_log = tmp_path / "DAY_001_FORWARD_TRADE_LOG.csv"
    write_csv(feed, [{"decision": "PAPER_SIGNAL_APPROVED", "symbol": "NIFTY"}])
    write_csv(
        trade_log,
        [
            {
                "paper_trade_id": "PT-1",
                "entry_time": "2026-07-09T10:00:00",
                "symbol": "NIFTY PE",
                "entry_price": "100",
                "exit_price": "120",
            }
        ],
    )

    payload = engine.evaluate_paper_signal_no_trade_reason(
        workspace=tmp_path,
        trading_date="2026-07-09",
        day_number=1,
    )

    assert payload["actual_paper_trades"] == 1
    assert payload["engine_decision"] == "ACTUAL_PAPER_TRADE_ROWS_PRESENT"
    assert payload["no_trade_reason"] == "TRADE_TAKEN_FROM_ACTUAL_PAPER_ROWS"
    assert payload["fake_trades_created"] is False


def test_guard_check_hard_blocks_order_and_tuning_actions():
    payload = engine.guard_check()

    assert payload["guard_check_status"] == "PASS"
    assert payload["blocked_actions"]["place_order"] == "HARD_BLOCKED"
    assert payload["blocked_actions"]["candidate_parameter_tuning"] == "HARD_BLOCKED"
    assert payload["blocked_actions"]["fake_trade_injection"] == "HARD_BLOCKED"
    assert payload["safety_lock"]["no_real_orders"] is True
    assert payload["safety_lock"]["no_candidate_tuning_during_validation"] is True
