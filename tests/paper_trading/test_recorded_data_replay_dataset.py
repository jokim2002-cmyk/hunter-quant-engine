import json
from pathlib import Path

from src.paper_trading.recorded_data_replay_dataset import (
    ReplayDatasetReport,
    ReplaySourceSummary,
    build_and_write_replay_dataset,
    build_replay_dataset,
    discover_recorded_files,
    normalize_file,
    normalize_mapping,
    paths_from_inventory,
    safety_notice,
    write_replay_dataset,
)


def test_normalize_mapping_with_full_ohlcv_fields():
    record = normalize_mapping(
        {
            "timestamp": "2026-01-01T09:15:00+05:30",
            "open": "100",
            "high": "110",
            "low": "95",
            "close": "105",
            "volume": "1,200",
        },
        source_path="sample.csv",
        source_type="csv",
        row_number=1,
    )

    assert record is not None
    assert record.timestamp == "2026-01-01T09:15:00+05:30"
    assert record.open == 100.0
    assert record.high == 110.0
    assert record.low == 95.0
    assert record.close == 105.0
    assert record.volume == 1200.0
    assert record.missing_fields == []


def test_normalize_mapping_supports_common_aliases():
    record = normalize_mapping(
        {"Time": "09:20", "O": 10, "H": 12, "L": 9, "C": 11, "Vol": 50},
        source_path="alias.csv",
        source_type="csv",
        row_number=1,
    )

    assert record is not None
    assert record.timestamp == "09:20"
    assert record.open == 10.0
    assert record.high == 12.0
    assert record.low == 9.0
    assert record.close == 11.0
    assert record.volume == 50.0


def test_normalize_mapping_returns_none_when_no_replay_fields_exist():
    assert (
        normalize_mapping(
            {"symbol": "NIFTY", "note": "no prices"},
            source_path="bad.csv",
            source_type="csv",
            row_number=1,
        )
        is None
    )


def test_csv_file_is_normalized(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01T09:15:00+05:30,100,110,95,105,1000\n",
        encoding="utf-8",
    )

    records, summary = normalize_file(source)

    assert summary.status == "parsed"
    assert summary.discovered_records == 1
    assert len(records) == 1
    assert records[0].close == 105.0


def test_csv_file_tracks_missing_fields(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text("timestamp,close\n09:15,101\n", encoding="utf-8")

    records, summary = normalize_file(source)

    assert summary.normalized_records == 1
    assert records[0].missing_fields == ["open", "high", "low", "volume"]


def test_json_list_file_is_normalized(tmp_path):
    source = tmp_path / "sample.json"
    source.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-01-01T09:15:00+05:30",
                    "open": 1,
                    "high": 2,
                    "low": 0.5,
                    "close": 1.5,
                    "volume": 10,
                }
            ]
        ),
        encoding="utf-8",
    )

    records, summary = normalize_file(source)

    assert summary.status == "parsed"
    assert len(records) == 1
    assert records[0].open == 1.0


def test_json_nested_data_file_is_normalized(tmp_path):
    source = tmp_path / "sample.json"
    source.write_text(
        json.dumps({"data": [{"time": "09:15", "o": 1, "h": 2, "l": 1, "c": 2}]}),
        encoding="utf-8",
    )

    records, summary = normalize_file(source)

    assert summary.discovered_records == 1
    assert records[0].timestamp == "09:15"
    assert records[0].close == 2.0


def test_json_single_object_file_is_normalized(tmp_path):
    source = tmp_path / "sample.json"
    source.write_text(
        json.dumps({"datetime": "09:15", "price": 22250}),
        encoding="utf-8",
    )

    records, summary = normalize_file(source)

    assert summary.normalized_records == 1
    assert records[0].close == 22250.0


def test_jsonl_file_is_normalized_and_bad_lines_are_skipped(tmp_path):
    source = tmp_path / "sample.jsonl"
    source.write_text(
        json.dumps({"timestamp": "09:15", "open": 1, "high": 2, "low": 1, "close": 2})
        + "\nnot-json\n"
        + json.dumps({"note": "missing prices"})
        + "\n",
        encoding="utf-8",
    )

    records, summary = normalize_file(source)

    assert summary.status == "parsed"
    assert len(records) == 1
    assert summary.skipped_records == 2


def test_parquet_file_is_discovered_but_skipped(tmp_path):
    source = tmp_path / "sample.parquet"
    source.write_bytes(b"PAR1")

    records, summary = normalize_file(source)

    assert records == []
    assert summary.status == "skipped"
    assert "deferred" in summary.message


def test_discover_recorded_files_finds_supported_files_only(tmp_path):
    root = tmp_path / "recorded"
    nested = root / "nested"
    nested.mkdir(parents=True)
    csv_path = root / "a.csv"
    json_path = nested / "b.jsonl"
    txt_path = root / "ignore.txt"
    csv_path.write_text("timestamp,close\n09:15,1\n", encoding="utf-8")
    json_path.write_text('{"timestamp":"09:16","close":2}\n', encoding="utf-8")
    txt_path.write_text("ignore", encoding="utf-8")

    discovered = discover_recorded_files([root])

    assert csv_path in discovered
    assert json_path in discovered
    assert txt_path not in discovered


def test_paths_from_inventory_reads_tolerant_inventory_schema(tmp_path, monkeypatch):
    source = tmp_path / "data" / "sample.csv"
    source.parent.mkdir()
    source.write_text("timestamp,close\n09:15,1\n", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps({"files": [{"file_path": str(source)}]}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    paths = paths_from_inventory(inventory)

    assert paths == [source]


def test_build_replay_dataset_deduplicates_inventory_and_discovery(tmp_path):
    root = tmp_path / "recorded"
    root.mkdir()
    source = root / "sample.csv"
    source.write_text("timestamp,close\n09:15,1\n", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps({"sources": [{"path": str(source)}]}),
        encoding="utf-8",
    )

    report = build_replay_dataset(
        inventory_path=inventory,
        recorded_roots=[root],
        output_dir=tmp_path / "out",
    )

    assert report.source_count == 1
    assert report.normalized_record_count == 1


def test_write_replay_dataset_creates_all_outputs(tmp_path):
    report = ReplayDatasetReport(
        generated_at_utc="2026-01-01T00:00:00+00:00",
        source_count=1,
        normalized_record_count=0,
        output_directory=str(tmp_path),
        safety_notice=safety_notice(),
        sources=[
            ReplaySourceSummary(
                path="sample.csv",
                file_type="csv",
                status="parsed",
                discovered_records=0,
                normalized_records=0,
                skipped_records=0,
                message="ok",
            )
        ],
        records=[],
    )

    outputs = write_replay_dataset(report, tmp_path / "out")

    assert outputs["dataset_json"].exists()
    assert outputs["dataset_jsonl"].exists()
    assert outputs["dataset_txt"].exists()
    assert outputs["manifest_json"].exists()
    assert "not a profitability claim" in outputs["dataset_txt"].read_text(
        encoding="utf-8"
    )


def test_build_and_write_replay_dataset_includes_safety_notice(tmp_path):
    root = tmp_path / "recorded"
    root.mkdir()
    (root / "sample.jsonl").write_text(
        '{"timestamp":"09:15","open":1,"high":2,"low":1,"close":2,"volume":10}\n',
        encoding="utf-8",
    )

    report, outputs = build_and_write_replay_dataset(
        inventory_path=tmp_path / "missing_inventory.json",
        recorded_roots=[root],
        output_dir=tmp_path / "out",
    )

    assert report.normalized_record_count == 1
    text_report = outputs["dataset_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    assert "Paper/simulation evidence only" in text_report
    assert "prove profitability" in manifest["safety_notice"]


def test_documentation_mentions_replay_dataset_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_REPLAY_DATASET.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_replay_dataset.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
