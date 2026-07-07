import json
from pathlib import Path

from src.paper_trading.real_dataset_backtest_input_pack import (
    build_and_write_real_dataset_input_pack_report,
    build_real_dataset_input_pack_report,
    safety_notice,
)


def _write(path: Path, content: str = "timestamp,open,high,low,close,volume\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_safety_notice_preserves_real_dataset_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation real dataset backtest input pack" in notice
    assert "saved recorded-data files" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_input_directory_fails_by_default(tmp_path):
    report = build_real_dataset_input_pack_report(
        input_directories=[tmp_path / "missing"],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_first_real_backtest_run is False
    assert any(issue.code == "input_directories_missing" for issue in report.issues)
    assert any(issue.code == "no_supported_recorded_dataset_files" for issue in report.issues)


def test_empty_directory_fails_by_default(tmp_path):
    data_dir = tmp_path / "recorded"
    data_dir.mkdir()

    report = build_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.discovered_file_count == 0
    assert report.ready_for_future_first_real_backtest_run is False


def test_empty_directory_can_warn_when_allowed(tmp_path):
    data_dir = tmp_path / "recorded"
    data_dir.mkdir()

    report = build_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
        allow_empty=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_first_real_backtest_run is False


def test_supported_dataset_files_are_discovered(tmp_path):
    data_dir = tmp_path / "recorded"
    csv_path = _write(data_dir / "nifty.csv")
    jsonl_path = _write(data_dir / "ticks.jsonl", "{}\n")

    report = build_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
    )

    paths = {file.path for file in report.files}

    assert report.status == "pass"
    assert report.ready_for_future_first_real_backtest_run is True
    assert report.discovered_file_count == 2
    assert str(csv_path) in paths
    assert str(jsonl_path) in paths
    assert report.selected_dataset_path == str(csv_path)


def test_unsupported_files_are_ignored(tmp_path):
    data_dir = tmp_path / "recorded"
    _write(data_dir / "notes.txt", "ignore\n")
    _write(data_dir / "data.csv")

    report = build_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.discovered_file_count == 1
    assert report.files[0].extension == ".csv"


def test_min_files_rule_can_fail(tmp_path):
    data_dir = tmp_path / "recorded"
    _write(data_dir / "data.csv")

    report = build_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
        min_files=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_recorded_dataset_files" for issue in report.issues)


def test_nested_files_are_discovered(tmp_path):
    data_dir = tmp_path / "recorded"
    nested = _write(data_dir / "2026" / "sample.parquet", "dummy")

    report = build_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.discovered_file_count == 1
    assert report.files[0].path == str(nested)
    assert report.files[0].extension == ".parquet"


def test_build_and_write_outputs_include_commands(tmp_path):
    data_dir = tmp_path / "recorded"
    _write(data_dir / "sample.csv")

    report, outputs = build_and_write_real_dataset_input_pack_report(
        input_directories=[data_dir],
        output_dir=tmp_path / "out",
    )

    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))
    commands = outputs["real_dataset_backtest_commands_txt"].read_text(encoding="utf-8")
    text = outputs["real_dataset_backtest_input_pack_txt"].read_text(encoding="utf-8")

    assert report.status == "pass"
    assert outputs["real_dataset_backtest_input_pack_json"].exists()
    assert "hqe_recorded_data_backtest_readiness_gate.bat" in commands
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_first_real_backtest_run"] is True


def test_docs_reference_real_dataset_input_pack():
    doc_paths = [
        Path("docs/REAL_DATASET_BACKTEST_INPUT_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_real_dataset_backtest_input_pack.bat" in combined_docs
    assert "real dataset backtest input pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()


def test_progress_metadata_in_docs():
    doc = Path("docs/REAL_DATASET_BACKTEST_INPUT_PACK.md").read_text(encoding="utf-8")

    assert "Completed total before Module LLL: 63 modules" in doc
    assert "Phase 1 pending before Module LLL: 10 modules" in doc
    assert "Phase 1 pending after Module LLL: 9 modules" in doc
