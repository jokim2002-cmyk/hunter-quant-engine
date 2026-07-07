import json
from pathlib import Path

from src.paper_trading.strategy_mode_backtest_result_comparison_pack import (
    build_and_write_strategy_mode_backtest_result_comparison_report,
    build_strategy_mode_backtest_result_comparison_report,
    safety_notice,
)


MODES = ["strict", "balanced", "relaxed"]
CATEGORIES = [
    "backtest_trade_ledger.json",
    "backtest_metrics.json",
    "backtest_report.json",
    "backtest_readiness_gate.json",
]


def _write(path: Path, text: str = "{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _mode_output_dir(tmp_path, mode_name, create_outputs=True):
    output_dir = tmp_path / "mode_backtests" / mode_name

    if create_outputs:
        for filename in CATEGORIES:
            _write(output_dir / filename)

    return output_dir


def _run(tmp_path, mode_name, create_outputs=True):
    output_dir = _mode_output_dir(tmp_path, mode_name, create_outputs=create_outputs)
    return {
        "run_index": 1,
        "mode_name": mode_name,
        "command": f".\\hqe_recorded_data_one_command_backtest_runner.bat --mode {mode_name}",
        "mode_config_reference": f"strategy_mode_definitions.csv::{mode_name}",
        "expected_output_directory": str(output_dir),
        "purpose": f"{mode_name} paper-only mode run",
    }


def _run_matrix(tmp_path, status="pass", ready=True, modes=None, create_outputs=True, issues=None):
    if modes is None:
        modes = MODES

    runs = [_run(tmp_path, mode, create_outputs=create_outputs) for mode in modes]

    return {
        "status": status,
        "ready_for_future_mode_backtest_execution": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "mode_count": len(runs),
        "run_count": len(runs),
        "safety_notice": "paper/simulation strategy mode backtest run matrix pack only",
        "issues": [] if issues is None else issues,
        "runs": runs,
        "mode_names": modes,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_result_comparison_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation strategy mode backtest result comparison pack" in notice
    assert "strict, balanced, and relaxed" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_run_matrix_pack_fails(tmp_path):
    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_cost_adjusted_mode_comparison is False
    assert any(issue.code == "strategy_mode_backtest_run_matrix_pack_missing" for issue in report.issues)


def test_invalid_json_run_matrix_pack_fails(tmp_path):
    path = tmp_path / "run_matrix.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_backtest_run_matrix_pack_invalid_json" for issue in report.issues)


def test_valid_run_matrix_with_existing_outputs_passes(tmp_path):
    path = _write_json(tmp_path / "run_matrix.json", _run_matrix(tmp_path))

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_cost_adjusted_mode_comparison is True
    assert report.mode_count == 3
    assert report.expected_result_path_count == 12
    assert report.existing_result_path_count == 12
    assert report.missing_result_path_count == 0
    assert {summary.mode_name for summary in report.mode_summaries} == {"strict", "balanced", "relaxed"}


def test_missing_mode_outputs_fail_by_default(tmp_path):
    path = _write_json(
        tmp_path / "run_matrix.json",
        _run_matrix(tmp_path, create_outputs=False),
    )

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_result_path_count == 12
    assert any(issue.code == "strategy_mode_backtest_result_outputs_missing_on_disk" for issue in report.issues)


def test_mode_output_existence_check_can_be_skipped(tmp_path):
    path = _write_json(
        tmp_path / "run_matrix.json",
        _run_matrix(tmp_path, create_outputs=False),
    )

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
        require_mode_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.ready_for_future_cost_adjusted_mode_comparison is True
    assert report.missing_result_path_count == 12


def test_warning_run_matrix_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "run_matrix.json",
        _run_matrix(tmp_path, status="warn", ready=True),
    )

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_backtest_run_matrix_pack_warn" for issue in report.issues)


def test_warning_run_matrix_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "run_matrix.json",
        _run_matrix(tmp_path, status="warn", ready=True),
    )

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_cost_adjusted_mode_comparison is True


def test_not_ready_run_matrix_fails(tmp_path):
    path = _write_json(
        tmp_path / "run_matrix.json",
        _run_matrix(tmp_path, status="pass", ready=False),
    )

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_backtest_run_matrix_pack_not_ready" for issue in report.issues)


def test_missing_required_modes_fail(tmp_path):
    path = _write_json(
        tmp_path / "run_matrix.json",
        _run_matrix(tmp_path, modes=["strict", "balanced"]),
    )

    report = build_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.mode_count == 2
    assert any(issue.code == "required_strategy_mode_result_runs_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "run_matrix.json", _run_matrix(tmp_path))

    report, outputs = build_and_write_strategy_mode_backtest_result_comparison_report(
        run_matrix_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["strategy_mode_backtest_result_comparison_pack_txt"].read_text(encoding="utf-8")
    result_paths_csv = outputs["strategy_mode_backtest_result_paths_csv"].read_text(encoding="utf-8")
    summary_csv = outputs["strategy_mode_backtest_result_summary_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/STRATEGY_MODE_BACKTEST_RESULT_COMPARISON_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["strategy_mode_backtest_result_comparison_pack_json"].exists()
    assert "mode_name,category,required,exists,path" in result_paths_csv
    assert "mode_name,expected_output_count,existing_output_count,missing_output_count" in summary_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_cost_adjusted_mode_comparison"] is True
    assert "hqe_strategy_mode_backtest_result_comparison_pack.bat" in combined_docs
    assert "strategy mode backtest result comparison pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
