from __future__ import annotations

import csv
from pathlib import Path

from scripts.close_forward_validation_day import (
    SAFETY_LOCK,
    TRADE_LEDGER_COLUMNS,
    close_forward_validation_day,
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_LEDGER_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in TRADE_LEDGER_COLUMNS})


def test_module145_records_zero_trade_day_without_master_trade_row(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()

    trade_log = active / "DAY_001_FORWARD_TRADE_LOG.csv"
    master = active / "FORWARD_VALIDATION_MASTER_LEDGER.csv"
    _write_csv(trade_log, [])
    _write_csv(master, [])

    runs_root = tmp_path / "runs"
    module140 = runs_root / "HQE_MODULE_140_DAILY_WORKFLOW_20260709_143713"
    module144 = runs_root / "HQE_MODULE_144_OPERATOR_CONTROL_CENTER_20260709_143731"
    module140.mkdir(parents=True)
    module144.mkdir(parents=True)
    (module140 / "MODULE_140_DAILY_WORKFLOW_MODEL.json").write_text("{}", encoding="utf-8")
    (module144 / "MODULE_144_OPERATOR_CONTROL_CENTER.json").write_text("{}", encoding="utf-8")

    result = close_forward_validation_day(
        active_dir=active,
        day_number=1,
        trading_date="2026-07-09",
        runs_root=runs_root,
    )

    assert result["day_status"] == "ZERO_TRADE_DAY_RECORDED"
    assert result["trade_count"] == 0
    assert result["master_rows_appended"] == 0
    assert result["safety_lock"] == SAFETY_LOCK
    assert result["safety_lock"]["fake_trades"] is False
    assert Path(result["json_path"]).exists()
    assert Path(result["markdown_path"]).exists()

    master_rows = list(csv.DictReader(master.open("r", encoding="utf-8")))
    assert master_rows == []

    day_rows = list(csv.DictReader((active / "FORWARD_VALIDATION_DAY_LEDGER.csv").open("r", encoding="utf-8")))
    assert len(day_rows) == 1
    assert day_rows[0]["trade_count"] == "0"
    assert day_rows[0]["day_status"] == "ZERO_TRADE_DAY_RECORDED"

    markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "This is not a profitability claim" in markdown
    assert "Fake trades: `NO`" in markdown


def test_module145_syncs_actual_trades_only_when_enabled(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()

    row = {
        "date": "2026-07-09",
        "day_number": "1",
        "trade_number": "1",
        "expiry_week": "2026-W28",
        "symbol": "NIFTY_PE_PAPER",
        "side": "PE_BUY_PAPER",
        "entry_time": "10:00",
        "entry_price": "100",
        "exit_time": "10:30",
        "exit_price": "120",
        "quantity": "75",
        "gross_pnl": "1500",
        "estimated_charges": "100",
        "net_pnl": "1400",
        "exit_reason": "TARGET_PAPER",
        "rule_match": "YES",
        "data_quality_ok": "YES",
        "manual_override": "NO",
        "notes": "paper only",
    }

    trade_log = active / "DAY_001_FORWARD_TRADE_LOG.csv"
    master = active / "FORWARD_VALIDATION_MASTER_LEDGER.csv"
    _write_csv(trade_log, [row])
    _write_csv(master, [])

    result = close_forward_validation_day(
        active_dir=active,
        day_number=1,
        trading_date="2026-07-09",
        sync_master_ledger=True,
    )

    assert result["day_status"] == "TRADE_DAY_RECORDED"
    assert result["trade_count"] == 1
    assert result["net_pnl"] == 1400.0
    assert result["master_rows_appended"] == 1

    master_rows = list(csv.DictReader(master.open("r", encoding="utf-8")))
    assert len(master_rows) == 1
    assert master_rows[0]["trade_number"] == "1"

    result2 = close_forward_validation_day(
        active_dir=active,
        day_number=1,
        trading_date="2026-07-09",
        sync_master_ledger=True,
    )
    assert result2["master_rows_appended"] == 0

    master_rows2 = list(csv.DictReader(master.open("r", encoding="utf-8")))
    assert len(master_rows2) == 1

    day_rows = list(csv.DictReader((active / "FORWARD_VALIDATION_DAY_LEDGER.csv").open("r", encoding="utf-8")))
    assert len(day_rows) == 1


def test_module145_does_not_sync_master_by_default(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()

    row = {
        "date": "2026-07-09",
        "day_number": "1",
        "trade_number": "1",
        "net_pnl": "100",
        "data_quality_ok": "YES",
        "manual_override": "NO",
    }

    trade_log = active / "DAY_001_FORWARD_TRADE_LOG.csv"
    master = active / "FORWARD_VALIDATION_MASTER_LEDGER.csv"
    _write_csv(trade_log, [row])
    _write_csv(master, [])

    result = close_forward_validation_day(
        active_dir=active,
        day_number=1,
        trading_date="2026-07-09",
    )

    assert result["trade_count"] == 1
    assert result["master_rows_appended"] == 0
    assert list(csv.DictReader(master.open("r", encoding="utf-8"))) == []


def test_module145_rejects_bad_trade_log_schema(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()

    bad_log = active / "DAY_001_FORWARD_TRADE_LOG.csv"
    bad_log.write_text("date,day_number\n2026-07-09,1\n", encoding="utf-8")
    _write_csv(active / "FORWARD_VALIDATION_MASTER_LEDGER.csv", [])

    try:
        close_forward_validation_day(active_dir=active, day_number=1, trading_date="2026-07-09")
    except ValueError as exc:
        assert "schema missing columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError for bad schema")


def test_module145_accepts_utf8_bom_csv_headers(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir()

    header = ",".join(TRADE_LEDGER_COLUMNS)
    # Simulate a Windows/PowerShell UTF-8 BOM file where the first header is visually
    # "date" but Python would otherwise read it as "\ufeffdate".
    (active / "DAY_001_FORWARD_TRADE_LOG.csv").write_text(
        "\ufeff" + header + "\n",
        encoding="utf-8",
    )
    _write_csv(active / "FORWARD_VALIDATION_MASTER_LEDGER.csv", [])

    result = close_forward_validation_day(
        active_dir=active,
        day_number=1,
        trading_date="2026-07-09",
    )

    assert result["day_status"] == "ZERO_TRADE_DAY_RECORDED"
    assert result["trade_count"] == 0
    assert Path(result["day_ledger_path"]).exists()
