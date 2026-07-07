import json
from pathlib import Path

from src.paper_trading.recorded_backtest_run_output_intake_pack import (
    build_and_write_recorded_backtest_run_output_intake_report,
    build_recorded_backtest_run_output_intake_report,
    safety_notice,
)


COMMAND_STEPS = [
    "confirm_git_clean",
    "build_real_dataset_input_pack",
    "build_first_real_dataset_run_pack",
    "run_existing_one_command_backtest",
    "verify_first_real_backtest_outputs",
    "review_first_real_backtest_report",
    "preserve_generated_outputs_ignored",
]


def _command_step(index, name):
    return {
        "command_index": index,
        "command_name": name,
        "command_text": f"{name}.bat",
        "stage": "manual_run",
        "expected_output": f"{name} expected",
        "safety_boundary": f"{name} safety",
    }


def _command_plan(status="pass", ready=True, steps=None, issues=None):
    if steps is None:
        steps = [
            _command_step(index, name)
            for index, name in enumerate(COMMAND_STEPS, start=1)
        ]

    return {
        "status": status,
        "ready_for_manual_operator_run": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "command_step_count": len(steps),
        "launch_step_count": 7,
        "completed_total_after_module": 83,
        "phase_3_pending_after_module": 4,
        "full_hqe_product_estimate_after_module": "75-80%",
        "recommended_next_action": "manual operator run",
        "safety_notice": "paper/simulation recorded backtest command plan pack only",
        "issues": [] if issues is None else issues,
        "command_steps": steps,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_recorded_backtest_output_intake_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation recorded backtest run output intake pack" in notice
    assert "post-run output intake expectations" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_recorded_backtest_command_plan_fails(tmp_path):
    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_post_run_output_verification is False
    assert any(issue.code == "recorded_backtest_command_plan_pack_missing" for issue in report.issues)


def test_invalid_json_recorded_backtest_command_plan_fails(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_command_plan_pack_invalid_json" for issue in report.issues)


def test_valid_command_plan_creates_output_intake(tmp_path):
    path = _write_json(tmp_path / "plan.json", _command_plan())

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    output_names = {item.output_name for item in report.expected_outputs}

    assert report.status == "pass"
    assert report.ready_for_post_run_output_verification is True
    assert report.expected_output_count == 8
    assert report.command_step_count == 7
    assert "backtest_trade_ledger" in output_names
    assert "backtest_metrics" in output_names
    assert "backtest_report" in output_names
    assert "git_generated_outputs_guard" in output_names
    assert report.selected_dataset_path == "data/recorded/sample.csv"
    assert report.completed_total_before_module == 83
    assert report.completed_total_after_module == 84
    assert report.phase_3_pending_after_module == 3
    assert report.full_hqe_product_estimate_after_module == "76-81%"


def test_warning_command_plan_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _command_plan(status="warn", ready=True),
    )

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_command_plan_pack_warn" for issue in report.issues)


def test_warning_command_plan_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _command_plan(status="warn", ready=True),
    )

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_post_run_output_verification is True


def test_not_ready_command_plan_fails(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _command_plan(status="pass", ready=False),
    )

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_command_plan_pack_not_ready" for issue in report.issues)


def test_command_plan_fail_issues_fail_output_intake(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _command_plan(
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

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_command_plan_contains_fail_issues" for issue in report.issues)


def test_missing_required_command_steps_fail(tmp_path):
    steps = [
        _command_step(index, name)
        for index, name in enumerate(COMMAND_STEPS[:3], start=1)
    ]
    path = _write_json(tmp_path / "plan.json", _command_plan(steps=steps))

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_recorded_backtest_command_steps_missing" for issue in report.issues)


def test_forbidden_command_plan_fields_fail(tmp_path):
    payload = _command_plan()
    payload["broker"] = "forbidden"
    path = _write_json(tmp_path / "plan.json", payload)

    report = build_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_command_plan_forbidden_fields" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "plan.json", _command_plan())

    report, outputs = build_and_write_recorded_backtest_run_output_intake_report(
        recorded_backtest_command_plan_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["recorded_backtest_run_output_intake_pack_txt"].read_text(encoding="utf-8")
    outputs_csv = outputs["recorded_backtest_expected_outputs_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_BACKTEST_RUN_OUTPUT_INTAKE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["recorded_backtest_run_output_intake_pack_json"].exists()
    assert "expectation_index,output_name,expected_path_hint,required_after_manual_run,producer_stage,intake_check,safety_boundary" in outputs_csv
    assert "backtest_trade_ledger" in outputs_csv
    assert "git_generated_outputs_guard" in outputs_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_post_run_output_verification"] is True
    assert "hqe_recorded_backtest_run_output_intake_pack.bat" in combined_docs
    assert "recorded backtest run output intake pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module FFFF: 84 modules" in combined_docs
