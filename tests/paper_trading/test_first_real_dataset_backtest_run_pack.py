import json
from pathlib import Path

from src.paper_trading.first_real_dataset_backtest_run_pack import (
    build_and_write_first_backtest_run_pack_report,
    build_first_backtest_run_pack_report,
    safety_notice,
)


def _dataset(tmp_path):
    path = tmp_path / "recorded" / "sample.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "timestamp,open,high,low,close,volume\n2026-01-01T09:15:00+05:30,100,101,99,100,1000\n",
        encoding="utf-8",
    )
    return path


def _input_pack(tmp_path, status="pass", ready=True, dataset_path=None, discovered_file_count=1, issues=None):
    if dataset_path is None:
        dataset_path = _dataset(tmp_path)

    return {
        "status": status,
        "ready_for_future_first_real_backtest_run": ready,
        "selected_dataset_path": str(dataset_path),
        "discovered_file_count": discovered_file_count,
        "supported_extensions": [".csv", ".json", ".jsonl", ".parquet"],
        "safety_notice": "paper/simulation real dataset backtest input pack only",
        "issues": [] if issues is None else issues,
        "files": [
            {
                "path": str(dataset_path),
                "extension": Path(str(dataset_path)).suffix,
                "size_bytes": 100,
            }
        ],
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_first_run_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation first real dataset backtest run pack" in notice
    assert "operator run order" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_input_pack_fails(tmp_path):
    report = build_first_backtest_run_pack_report(
        input_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_operator_first_real_backtest_run is False
    assert any(issue.code == "real_dataset_input_pack_missing" for issue in report.issues)


def test_invalid_json_input_pack_fails(tmp_path):
    path = tmp_path / "input_pack.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "real_dataset_input_pack_invalid_json" for issue in report.issues)


def test_valid_input_pack_creates_first_run_pack(tmp_path):
    path = _write_json(tmp_path / "input_pack.json", _input_pack(tmp_path))

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_operator_first_real_backtest_run is True
    assert report.command_count == 8
    assert report.expected_output_count == 9
    assert report.discovered_file_count == 1
    assert any("hqe_recorded_data_backtest_readiness_gate.bat" in command.command for command in report.commands)


def test_warning_input_pack_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "input_pack.json",
        _input_pack(tmp_path, status="warn", ready=True),
    )

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "real_dataset_input_pack_warn" for issue in report.issues)


def test_warning_input_pack_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "input_pack.json",
        _input_pack(tmp_path, status="warn", ready=True),
    )

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_operator_first_real_backtest_run is True


def test_not_ready_input_pack_fails(tmp_path):
    path = _write_json(
        tmp_path / "input_pack.json",
        _input_pack(tmp_path, status="pass", ready=False),
    )

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "real_dataset_input_pack_not_ready" for issue in report.issues)


def test_selected_dataset_missing_on_disk_fails_by_default(tmp_path):
    missing_dataset = tmp_path / "recorded" / "missing.csv"
    path = _write_json(
        tmp_path / "input_pack.json",
        _input_pack(tmp_path, dataset_path=missing_dataset),
    )

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "selected_dataset_missing_on_disk" for issue in report.issues)


def test_selected_dataset_existence_check_can_be_skipped(tmp_path):
    missing_dataset = tmp_path / "recorded" / "missing.csv"
    path = _write_json(
        tmp_path / "input_pack.json",
        _input_pack(tmp_path, dataset_path=missing_dataset),
    )

    report = build_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
        require_selected_dataset_exists=False,
    )

    assert report.status == "pass"
    assert report.ready_for_operator_first_real_backtest_run is True


def test_build_and_write_outputs_include_command_bat(tmp_path):
    path = _write_json(tmp_path / "input_pack.json", _input_pack(tmp_path))

    report, outputs = build_and_write_first_backtest_run_pack_report(
        input_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["first_real_dataset_backtest_run_pack_txt"].read_text(encoding="utf-8")
    command_bat = outputs["first_real_dataset_backtest_run_commands_bat"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["first_real_dataset_backtest_run_pack_json"].exists()
    assert "hqe_recorded_data_inventory.bat" in command_bat
    assert "hqe_v1_testing_operator_handoff_pack.bat" in command_bat
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_operator_first_real_backtest_run"] is True


def test_docs_reference_first_real_dataset_backtest_run_pack():
    doc_paths = [
        Path("docs/FIRST_REAL_DATASET_BACKTEST_RUN_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_first_real_dataset_backtest_run_pack.bat" in combined_docs
    assert "first real dataset backtest run pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
