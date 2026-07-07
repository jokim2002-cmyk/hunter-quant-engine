"""Tests for recorded-data evidence inventory."""

from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.recorded_data_inventory import (
    build_recorded_data_inventory_report,
    format_recorded_data_inventory_report,
    main,
    recorded_data_inventory_report_to_dict,
    run_recorded_data_inventory,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def test_recorded_data_inventory_finds_supported_files(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "nifty.csv").write_text("timestamp,close\n1,24200\n", encoding="utf-8")
    (root / "notes.txt").write_text("ignore me\n", encoding="utf-8")

    report = build_recorded_data_inventory_report(
        [root],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is True
    assert report.file_count == 1
    assert report.empty_file_count == 0
    assert report.total_size_bytes > 0
    assert report.files[0].path.endswith("nifty.csv")
    assert report.files[0].suffix == ".csv"


def test_recorded_data_inventory_blocks_missing_root(tmp_path):
    report = build_recorded_data_inventory_report(
        [tmp_path / "missing"],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is False
    assert "no recorded data roots exist" in report.blocking_reasons
    assert "no supported recorded data files found" in report.blocking_reasons


def test_recorded_data_inventory_blocks_empty_files(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "empty.csv").write_text("", encoding="utf-8")

    report = build_recorded_data_inventory_report(
        [root],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is False
    assert report.file_count == 1
    assert report.empty_file_count == 1
    assert "empty recorded data files found: 1" in report.blocking_reasons


def test_recorded_data_inventory_blocks_no_supported_files(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "readme.txt").write_text("not supported\n", encoding="utf-8")

    report = build_recorded_data_inventory_report(
        [root],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is False
    assert report.file_count == 0
    assert "no supported recorded data files found" in report.blocking_reasons


def test_recorded_data_inventory_writes_outputs_under_reports(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "nifty.jsonl").write_text('{"close": 24200}\n', encoding="utf-8")

    report, paths = run_recorded_data_inventory(
        [root],
        output_dir=tmp_path / "reports" / "paper_trading" / "recorded_data_inventory",
        generated_at=_GENERATED_AT,
    )

    assert report.passed is True
    assert paths.inventory_json.exists()
    assert paths.inventory_text.exists()
    assert paths.manifest_json.exists()

    text = paths.inventory_text.read_text(encoding="utf-8")
    assert "Hunter Quant Engine - Recorded Data Evidence Inventory" in text
    assert "not a profitability claim" in text
    assert "passed gates: True" in text


def test_recorded_data_inventory_rejects_output_outside_reports(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "nifty.csv").write_text("timestamp,close\n1,24200\n", encoding="utf-8")

    with pytest.raises(ValueError, match="reports/"):
        run_recorded_data_inventory(
            [root],
            output_dir=tmp_path / "recorded_data_inventory",
            generated_at=_GENERATED_AT,
        )


def test_recorded_data_inventory_report_dict_is_json_safe(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "nifty.parquet").write_bytes(b"not-real-parquet-but-inventory-only")

    report = build_recorded_data_inventory_report(
        [root],
        generated_at=_GENERATED_AT,
    )

    payload = recorded_data_inventory_report_to_dict(report)

    assert payload["paper_evidence_pipeline_only"] is True
    assert payload["file_count"] == 1
    assert payload["files"][0]["suffix"] == ".parquet"
    assert payload["blocking_reasons"] == []


def test_recorded_data_inventory_format_is_trader_friendly(tmp_path):
    root = tmp_path / "data" / "recorded"
    root.mkdir(parents=True)
    (root / "nifty.json").write_text('{"close": 24200}\n', encoding="utf-8")

    report = build_recorded_data_inventory_report(
        [root],
        generated_at=_GENERATED_AT,
    )

    text = format_recorded_data_inventory_report(report)

    assert "Hunter Quant Engine - Recorded Data Evidence Inventory" in text
    assert "paper/evidence pipeline only" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text
    assert "supported file count: 1" in text


def test_recorded_data_inventory_main_handles_no_default_data(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 1

    out = capsys.readouterr().out

    assert "Recorded Data Evidence Inventory" in out
    assert "passed gates: False" in out
    assert "no recorded data roots exist" in out


def test_recorded_data_inventory_shortcut_points_to_safe_cli():
    text = Path("hqe_recorded_data_inventory.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.recorded_data_inventory" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_recorded_data_inventory_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/recorded_data_inventory.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_recorded_data_inventory_docs_define_boundary():
    text = Path("docs/RECORDED_DATA_EVIDENCE_INVENTORY.md").read_text(
        encoding="utf-8"
    )

    assert "It is not live trading." in text
    assert "It does not use broker APIs." in text
    assert "It does not use live market data." in text
    assert "It does not place real orders." in text
    assert "It does not claim profitability." in text
    assert ".\\hqe_recorded_data_inventory.bat" in text
