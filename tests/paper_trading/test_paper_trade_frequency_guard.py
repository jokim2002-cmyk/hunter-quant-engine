import json
from pathlib import Path

from src.paper_trading.paper_trade_frequency_guard import (
    apply_frequency_guard,
    build_and_write_guard,
    build_guard_summary,
    no_profitability_claim_notice,
    safety_notice,
)


def _row(index, decision, entry, exit_, result=100.0):
    return {
        "ledger_row_index": index,
        "decision": decision,
        "option_type": "CE" if decision == "LONG" else "PE",
        "option_action": "BUY",
        "entry_timestamp": entry,
        "exit_timestamp": exit_,
        "broker_execution_mode": "broker_disabled",
        "order_mode": "orders_not_created",
        "money_mode": "real_money_not_used",
        "simulated_gross_result": result,
    }


def _write_ledger(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "pass",
                "ledger_trade_count": len(rows),
                "ledger_rows": rows,
            }
        ),
        encoding="utf-8",
    )


def test_frequency_guard_reduces_every_candle_trades():
    rows = [
        _row(1, "LONG", "2026-01-01 09:15:00", "2026-01-01 09:20:00"),
        _row(2, "LONG", "2026-01-01 09:20:00", "2026-01-01 09:25:00"),
        _row(3, "LONG", "2026-01-01 09:25:00", "2026-01-01 09:30:00"),
        _row(4, "SHORT", "2026-01-01 09:40:00", "2026-01-01 09:45:00"),
    ]

    accepted, skipped, reasons = apply_frequency_guard(
        rows,
        cooldown_bars_after_exit=2,
        bar_minutes=5,
        max_trades_per_day=6,
        require_direction_change=True,
    )

    assert len(accepted) < len(rows)
    assert accepted[0]["decision"] == "LONG"
    assert skipped
    assert reasons


def test_frequency_guard_enforces_daily_cap():
    rows = [
        _row(1, "LONG", "2026-01-01 09:15:00", "2026-01-01 09:16:00"),
        _row(2, "SHORT", "2026-01-01 09:30:00", "2026-01-01 09:31:00"),
        _row(3, "LONG", "2026-01-01 09:45:00", "2026-01-01 09:46:00"),
    ]

    accepted, skipped, reasons = apply_frequency_guard(
        rows,
        cooldown_bars_after_exit=0,
        bar_minutes=5,
        max_trades_per_day=2,
        require_direction_change=True,
    )

    assert len(accepted) == 2
    assert len(skipped) == 1
    assert reasons["daily_trade_cap_reached"] == 1


def test_frequency_guard_rejects_unsafe_rows():
    unsafe = _row(1, "LONG", "2026-01-01 09:15:00", "2026-01-01 09:20:00")
    unsafe["broker_execution_mode"] = "broker_enabled"

    accepted, skipped, reasons = apply_frequency_guard([unsafe])

    assert accepted == []
    assert len(skipped) == 1
    assert reasons["unsafe_execution_fields"] == 1


def test_build_guard_summary_passes_with_guarded_rows(tmp_path):
    ledger = tmp_path / "ledger.json"
    rows = [
        _row(1, "LONG", "2026-01-01 09:15:00", "2026-01-01 09:20:00", 100.0),
        _row(2, "LONG", "2026-01-01 09:20:00", "2026-01-01 09:25:00", -50.0),
        _row(3, "SHORT", "2026-01-01 09:40:00", "2026-01-01 09:45:00", 200.0),
    ]
    _write_ledger(ledger, rows)

    summary, accepted, skipped = build_guard_summary(
        ledger_path=ledger,
        output_dir=tmp_path / "out",
        cooldown_bars_after_exit=2,
        bar_minutes=5,
        max_trades_per_day=6,
    )

    assert summary.status == "pass"
    assert summary.baseline_trade_count == 3
    assert summary.guarded_trade_count < 3
    assert accepted
    assert skipped


def test_build_and_write_guard_outputs(tmp_path):
    ledger = tmp_path / "ledger.json"
    rows = [
        _row(1, "LONG", "2026-01-01 09:15:00", "2026-01-01 09:20:00", 100.0),
        _row(2, "SHORT", "2026-01-01 09:40:00", "2026-01-01 09:45:00", -50.0),
    ]
    _write_ledger(ledger, rows)

    summary, outputs = build_and_write_guard(
        ledger_path=ledger,
        output_dir=tmp_path / "out",
        cooldown_bars_after_exit=1,
        bar_minutes=5,
    )

    assert summary.status == "pass"
    assert outputs["summary_json"].exists()
    assert outputs["guarded_ledger_json"].exists()
    assert outputs["guarded_rows_csv"].exists()
    assert outputs["skipped_rows_csv"].exists()


def test_guard_language_preserves_safety_scope():
    combined = " ".join([safety_notice(), no_profitability_claim_notice()]).lower()

    assert "paper/simulation" in combined
    assert "does not" in combined
    assert "connect to brokers" in combined
    assert "place real orders" in combined
    assert "use real money" in combined
    assert "not a profitability claim" in combined
