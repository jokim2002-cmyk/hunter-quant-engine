from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_forward_paper_auto_runner.py"
SPEC = importlib.util.spec_from_file_location("run_forward_paper_auto_runner", MODULE_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_locked_candidate_accepts_pe_dte_premium_range() -> None:
    row = {
        "symbol": "NIFTY26JUL24000PE",
        "side": "PE_BUY",
        "dte": "7",
        "last_traded_price": "100",
        "er20": "0.45",
        "signal_time": "2026-07-09 09:45:00",
    }

    decision = MODULE.locked_candidate_decision(row)

    assert decision.accepted is True
    assert decision.side == "PE_BUY"
    assert "premium_ok=100" in decision.reason
    assert "dte_ok=7" in decision.reason
    assert "er20_ok=0.45" in decision.reason


def test_locked_candidate_rejects_ce() -> None:
    row = {
        "symbol": "NIFTY26JUL24000CE",
        "side": "CE_BUY",
        "dte": "7",
        "last_traded_price": "100",
        "er20": "0.45",
    }

    decision = MODULE.locked_candidate_decision(row)

    assert decision.accepted is False
    assert "PE_BUY only" in decision.reason


def test_locked_candidate_rejects_bad_premium() -> None:
    row = {
        "symbol": "NIFTY26JUL24000PE",
        "side": "PE_BUY",
        "dte": "7",
        "last_traded_price": "250",
        "er20": "0.45",
    }

    decision = MODULE.locked_candidate_decision(row)

    assert decision.accepted is False
    assert "premium outside locked range" in decision.reason


def test_build_signal_log_writes_accepted_and_rejected(tmp_path: Path) -> None:
    scenario_csv = tmp_path / "scenario.csv"
    locked_csv = tmp_path / "locked.csv"
    signal_log = tmp_path / "signals.csv"
    rejected_log = tmp_path / "rejected.csv"

    with scenario_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["symbol", "side", "dte", "last_traded_price", "er20", "signal_time"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "NIFTY26JUL24000PE",
                "side": "PE_BUY",
                "dte": "7",
                "last_traded_price": "100",
                "er20": "0.45",
                "signal_time": "2026-07-09 09:45:00",
            }
        )
        writer.writerow(
            {
                "symbol": "NIFTY26JUL24000CE",
                "side": "CE_BUY",
                "dte": "7",
                "last_traded_price": "100",
                "er20": "0.45",
                "signal_time": "2026-07-09 09:50:00",
            }
        )

    counts = MODULE.build_signal_log(scenario_csv, locked_csv, signal_log, rejected_log)

    assert counts == {"source_rows": 2, "accepted_signals": 1, "rejected_signals": 1}

    with signal_log.open("r", encoding="utf-8") as handle:
        accepted_rows = list(csv.DictReader(handle))
    with rejected_log.open("r", encoding="utf-8") as handle:
        rejected_rows = list(csv.DictReader(handle))

    assert len(accepted_rows) == 1
    assert accepted_rows[0]["side"] == "PE_BUY"
    assert accepted_rows[0]["rule_match"] == "YES"
    assert len(rejected_rows) == 1
    assert rejected_rows[0]["rule_match"] == "NO"


def test_append_trades_to_master_ledger_dedupes(tmp_path: Path) -> None:
    trades_csv = tmp_path / "trades.csv"
    ledger_csv = tmp_path / "ledger.csv"

    with trades_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "date",
                "symbol",
                "side",
                "entry_time",
                "entry_price",
                "exit_time",
                "exit_price",
                "net_pnl",
                "gross_pnl",
                "estimated_charges",
                "exit_reason",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "date": "2026-07-09",
                "symbol": "NIFTY26JUL24000PE",
                "side": "PE_BUY",
                "entry_time": "2026-07-09 09:45:00",
                "entry_price": "100",
                "exit_time": "2026-07-09 10:15:00",
                "exit_price": "220",
                "net_pnl": "1000",
                "gross_pnl": "1200",
                "estimated_charges": "200",
                "exit_reason": "target_hit",
            }
        )

    first = MODULE.append_trades_to_master_ledger(trades_csv, ledger_csv, "001")
    second = MODULE.append_trades_to_master_ledger(trades_csv, ledger_csv, "001")

    assert first["rows_appended"] == 1
    assert first["duplicates_skipped"] == 0
    assert second["rows_appended"] == 0
    assert second["duplicates_skipped"] == 1

    with ledger_csv.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["rule_match"] == "YES"
    assert rows[0]["manual_override"] == "NO"

