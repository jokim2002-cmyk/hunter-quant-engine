import json
from pathlib import Path

from src.paper_trading.recorded_backtest_output_presence_verification_pack import (
    build_and_write_recorded_backtest_output_presence_report,
    build_recorded_backtest_output_presence_report,
    safety_notice,
)


OUTPUTS = [
    (
        "real_dataset_backtest_input_pack",
        "reports/paper_trading/real_dataset_backtest_input_pack/real_dataset_backtest_input_pack.json",
    ),
    (
        "first_real_dataset_backtest_run_pack",
        "reports/paper_trading/first_real_dataset_backtest_run_pack/first_real_dataset_backtest_run_pack.json",
    ),
    (
        "backtest_trade_ledger",
        "reports/paper_trading/backtest_trade_ledger/backtest_trade_ledger.csv",
    ),
    (
        "backtest_metrics",
        "reports/paper_trading/backtest_metrics/backtest_metrics.json",
    ),
    (
        "backtest_report",
        "reports/paper_trading/backtest_report/backtest_report.txt",
    ),
    (
        "first_real_backtest_output_verification",
        "reports/paper_trading/first_real_backtest_output_verification_pack/first_real_backtest_output_verification_pack.json",
    ),
    (
        "first_real_backtest_report_review",
        "reports/paper_trading/first_real_backtest_report_review_pack/first_real_backtest_report_review_pack.json",
    ),
    ("git_generated_outputs_guard", "git status --short"),
]


def _expected_outputs(outputs=None):
    if outputs is None:
        outputs = OUTPUTS

    rows = []
    for index, (name, path_hint) in enumerate(outputs, start=1):
        rows.append(
            {
                "expectation_index": index,
                "output_name": name,
                "expected_path_hint": path_hint,
                "required_after_manual_run": True,
                "producer_stage": "manual_backtest_run",
                "intake_check": f"{name} intake check",
                "safety_boundary": "paper only; not a profitability claim",
            }
        )
    return rows


def _intake(status="pass", ready=True, outputs=None, issues=None):
    expected_outputs = _expected_outputs(outputs)
    return {
        "status": status,
        "ready_for_post_run_output_verification": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "expected_output_count": len(expected_outputs),
        "command_step_count": 7,
        "completed_total_after_module": 84,
        "phase_3_pending_after_module": 3,
        "full_hqe_product_estimate_after_module": "76-81%",
        "recommended_next_action": "verify post-run outputs",
        "safety_notice": "paper/simulation recorded backtest run output intake pack only",
        "issues": [] if issues is None else issues,
        "expected_outputs": expected_outputs,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _create_required_files(project_root):
    for name, path_hint in OUTPUTS:
        if name == "git_generated_outputs_guard":
            continue
        path = project_root / path_hint
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")


def test_safety_notice_preserves_recorded_backtest_output_presence_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation recorded backtest output presence verification pack" in notice
    assert "expected recorded-data paper backtest output files are present" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_recorded_backtest_run_output_intake_fails(tmp_path):
    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert report.ready_for_recorded_backtest_review_summary is False
    assert any(
        issue.code == "recorded_backtest_run_output_intake_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_recorded_backtest_run_output_intake_fails(tmp_path):
    path = tmp_path / "intake.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_run_output_intake_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_intake_with_present_files_passes(tmp_path):
    _create_required_files(tmp_path)
    path = _write_json(tmp_path / "intake.json", _intake())

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    statuses = {check.output_name: check.check_status for check in report.presence_checks}

    assert report.status == "pass"
    assert report.ready_for_recorded_backtest_review_summary is True
    assert report.expected_output_count == 8
    assert report.presence_check_count == 8
    assert report.present_required_file_count == 7
    assert report.missing_required_file_count == 0
    assert statuses["git_generated_outputs_guard"] == "manual_check"
    assert report.completed_total_before_module == 84
    assert report.completed_total_after_module == 85
    assert report.phase_3_pending_after_module == 2
    assert report.full_hqe_product_estimate_after_module == "77-82%"


def test_warning_intake_fails_by_default(tmp_path):
    _create_required_files(tmp_path)
    path = _write_json(
        tmp_path / "intake.json",
        _intake(status="warn", ready=True),
    )

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_run_output_intake_pack_warn"
        for issue in report.issues
    )


def test_warning_intake_can_remain_warning_when_allowed(tmp_path):
    _create_required_files(tmp_path)
    path = _write_json(
        tmp_path / "intake.json",
        _intake(status="warn", ready=True),
    )

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_recorded_backtest_review_summary is True


def test_not_ready_intake_fails(tmp_path):
    _create_required_files(tmp_path)
    path = _write_json(
        tmp_path / "intake.json",
        _intake(status="pass", ready=False),
    )

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_run_output_intake_pack_not_ready"
        for issue in report.issues
    )


def test_intake_fail_issues_fail_presence_verification(tmp_path):
    _create_required_files(tmp_path)
    path = _write_json(
        tmp_path / "intake.json",
        _intake(
            issues=[
                {
                    "severity": "fail",
                    "code": "example_fail",
                    "count": 1,
                    "message": "example",
                }
            ]
        ),
    )

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_run_output_intake_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_expected_outputs_fail(tmp_path):
    partial_outputs = OUTPUTS[:3]
    for name, path_hint in partial_outputs:
        if name == "git_generated_outputs_guard":
            continue
        path = tmp_path / path_hint
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    path = _write_json(tmp_path / "intake.json", _intake(outputs=partial_outputs))

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_recorded_backtest_expected_outputs_missing"
        for issue in report.issues
    )


def test_missing_required_physical_files_fail(tmp_path):
    path = _write_json(tmp_path / "intake.json", _intake())

    report = build_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 7
    assert any(
        issue.code == "required_recorded_backtest_output_files_missing"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    _create_required_files(tmp_path)
    path = _write_json(tmp_path / "intake.json", _intake())

    report, outputs = build_and_write_recorded_backtest_output_presence_report(
        recorded_backtest_run_output_intake_path=path,
        output_dir=tmp_path / "out",
        project_root=tmp_path,
    )

    text = outputs["recorded_backtest_output_presence_verification_pack_txt"].read_text(
        encoding="utf-8"
    )
    checks_csv = outputs["recorded_backtest_output_presence_checks_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_BACKTEST_OUTPUT_PRESENCE_VERIFICATION_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["recorded_backtest_output_presence_verification_pack_json"].exists()
    assert "check_index,output_name,expected_path_hint,resolved_path" in checks_csv
    assert "backtest_trade_ledger" in checks_csv
    assert "git_generated_outputs_guard" in checks_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_recorded_backtest_review_summary"] is True
    assert "hqe_recorded_backtest_output_presence_verification_pack.bat" in combined_docs
    assert "recorded backtest output presence verification pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module GGGG: 85 modules" in combined_docs
