import json
from pathlib import Path

from src.paper_trading.strategy_mode_backtest_run_matrix_pack import (
    build_and_write_strategy_mode_backtest_run_matrix_report,
    build_strategy_mode_backtest_run_matrix_report,
    safety_notice,
)


MODES = ["strict", "balanced", "relaxed"]


def _mode(name):
    return {
        "mode_name": name,
        "description": f"{name} mode",
        "decision_threshold": 1.0,
        "max_holding_bars": 5,
        "stop_loss_points": 10.0,
        "target_points": 15.0,
        "neutral_filter": "medium",
        "quality_filter": "standard",
        "cost_assumption": "cost_reference_required",
        "session_window": "standard_session",
    }


def _comparison(status="pass", ready=True, modes=None, issues=None):
    if modes is None:
        modes = [_mode(name) for name in MODES]

    return {
        "status": status,
        "ready_for_future_paper_mode_backtest": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "mode_count": len(modes),
        "tuning_candidate_count": 8,
        "safety_notice": "paper/simulation strategy mode comparison pack only",
        "issues": [] if issues is None else issues,
        "modes": modes,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_run_matrix_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation strategy mode backtest run matrix pack" in notice
    assert "strict, balanced, and relaxed" in notice
    assert "does not run a backtest" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_mode_comparison_pack_fails(tmp_path):
    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_mode_backtest_execution is False
    assert any(issue.code == "strategy_mode_comparison_pack_missing" for issue in report.issues)


def test_invalid_json_mode_comparison_pack_fails(tmp_path):
    path = tmp_path / "comparison.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_comparison_pack_invalid_json" for issue in report.issues)


def test_valid_comparison_creates_three_run_matrix_entries(tmp_path):
    path = _write_json(tmp_path / "comparison.json", _comparison())

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    run_modes = [run.mode_name for run in report.runs]

    assert report.status == "pass"
    assert report.ready_for_future_mode_backtest_execution is True
    assert report.mode_count == 3
    assert report.run_count == 3
    assert run_modes == ["strict", "balanced", "relaxed"]


def test_run_matrix_commands_are_paper_backtest_commands(tmp_path):
    path = _write_json(tmp_path / "comparison.json", _comparison())

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert all("hqe_recorded_data_one_command_backtest_runner.bat" in run.command for run in report.runs)
    assert all("--mode" in run.command for run in report.runs)
    assert all("mode_backtests" in run.expected_output_directory for run in report.runs)


def test_warning_comparison_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(status="warn", ready=True),
    )

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_comparison_pack_warn" for issue in report.issues)


def test_warning_comparison_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(status="warn", ready=True),
    )

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_mode_backtest_execution is True


def test_not_ready_comparison_fails(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(status="pass", ready=False),
    )

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_comparison_pack_not_ready" for issue in report.issues)


def test_missing_required_modes_fail(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(modes=[_mode("strict"), _mode("balanced")]),
    )

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.run_count == 2
    assert any(issue.code == "required_strategy_modes_missing" for issue in report.issues)


def test_unexpected_extra_mode_warns(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(modes=[_mode("strict"), _mode("balanced"), _mode("relaxed"), _mode("experimental")]),
    )

    report = build_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.run_count == 3
    assert any(issue.code == "unexpected_strategy_modes_present" for issue in report.issues)


def test_build_and_write_outputs_include_matrix_csv_and_commands(tmp_path):
    path = _write_json(tmp_path / "comparison.json", _comparison())

    report, outputs = build_and_write_strategy_mode_backtest_run_matrix_report(
        mode_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["strategy_mode_backtest_run_matrix_pack_txt"].read_text(encoding="utf-8")
    matrix_csv = outputs["strategy_mode_backtest_run_matrix_csv"].read_text(encoding="utf-8")
    commands_bat = outputs["strategy_mode_backtest_run_matrix_commands_bat"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["strategy_mode_backtest_run_matrix_pack_json"].exists()
    assert "run_index,mode_name,command,mode_config_reference" in matrix_csv
    assert "Future run 1: strict" in commands_bat
    assert "Future run 2: balanced" in commands_bat
    assert "Future run 3: relaxed" in commands_bat
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_mode_backtest_execution"] is True


def test_docs_reference_strategy_mode_backtest_run_matrix_pack():
    doc_paths = [
        Path("docs/STRATEGY_MODE_BACKTEST_RUN_MATRIX_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_strategy_mode_backtest_run_matrix_pack.bat" in combined_docs
    assert "strategy mode backtest run matrix pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
