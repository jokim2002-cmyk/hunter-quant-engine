import json
from pathlib import Path

from src.paper_trading.recorded_backtest_command_plan_pack import (
    build_and_write_recorded_backtest_command_plan_report,
    build_recorded_backtest_command_plan_report,
    safety_notice,
)


LAUNCH_STEPS = [
    "confirm_recorded_dataset",
    "confirm_paper_only_mode",
    "review_dashboard_close",
    "prepare_existing_backtest_runner",
    "run_recorded_backtest_manually",
    "verify_outputs_after_run",
    "preserve_generated_reports_ignored",
]


def _launch_step(index, name):
    return {
        "step_index": index,
        "step_name": name,
        "stage": "manual_run",
        "operator_action": f"{name} action",
        "expected_result": f"{name} expected",
        "safety_boundary": f"{name} safety",
    }


def _launch_gate(status="pass", ready=True, steps=None, issues=None):
    if steps is None:
        steps = [
            _launch_step(index, name)
            for index, name in enumerate(LAUNCH_STEPS, start=1)
        ]

    return {
        "status": status,
        "ready_for_manual_recorded_backtest_run": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "launch_step_count": len(steps),
        "dashboard_close_checklist_item_count": 8,
        "completed_total_after_module": 82,
        "phase_3_pending_after_module": 5,
        "full_hqe_product_estimate_after_module": "74-79%",
        "recommended_next_action": "manual recorded-data paper backtest run",
        "safety_notice": "paper/simulation recorded backtest launch gate pack only",
        "issues": [] if issues is None else issues,
        "launch_steps": steps,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_recorded_backtest_command_plan_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation recorded backtest command plan pack" in notice
    assert "manual command steps" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_recorded_backtest_launch_gate_fails(tmp_path):
    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_manual_operator_run is False
    assert any(issue.code == "recorded_backtest_launch_gate_pack_missing" for issue in report.issues)


def test_invalid_json_recorded_backtest_launch_gate_fails(tmp_path):
    path = tmp_path / "gate.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_launch_gate_pack_invalid_json" for issue in report.issues)


def test_valid_launch_gate_creates_command_plan(tmp_path):
    path = _write_json(tmp_path / "gate.json", _launch_gate())

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    command_names = {step.command_name for step in report.command_steps}

    assert report.status == "pass"
    assert report.ready_for_manual_operator_run is True
    assert report.command_step_count == 7
    assert report.launch_step_count == 7
    assert "run_existing_one_command_backtest" in command_names
    assert "verify_first_real_backtest_outputs" in command_names
    assert report.selected_dataset_path == "data/recorded/sample.csv"
    assert report.completed_total_before_module == 82
    assert report.completed_total_after_module == 83
    assert report.phase_3_pending_after_module == 4
    assert report.full_hqe_product_estimate_after_module == "75-80%"


def test_warning_launch_gate_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "gate.json",
        _launch_gate(status="warn", ready=True),
    )

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_launch_gate_pack_warn" for issue in report.issues)


def test_warning_launch_gate_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "gate.json",
        _launch_gate(status="warn", ready=True),
    )

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_manual_operator_run is True


def test_not_ready_launch_gate_fails(tmp_path):
    path = _write_json(
        tmp_path / "gate.json",
        _launch_gate(status="pass", ready=False),
    )

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_launch_gate_pack_not_ready" for issue in report.issues)


def test_launch_gate_fail_issues_fail_command_plan(tmp_path):
    path = _write_json(
        tmp_path / "gate.json",
        _launch_gate(
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

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "recorded_backtest_launch_gate_contains_fail_issues" for issue in report.issues)


def test_missing_required_launch_steps_fail(tmp_path):
    steps = [
        _launch_step(index, name)
        for index, name in enumerate(LAUNCH_STEPS[:3], start=1)
    ]
    path = _write_json(tmp_path / "gate.json", _launch_gate(steps=steps))

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_recorded_backtest_launch_steps_missing" for issue in report.issues)


def test_empty_dataset_uses_replace_placeholder(tmp_path):
    payload = _launch_gate()
    payload["selected_dataset_path"] = ""
    path = _write_json(tmp_path / "gate.json", payload)

    report = build_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.selected_dataset_path == "data/recorded/REPLACE_WITH_RECORDED_DATASET.csv"
    assert "REPLACE_WITH_RECORDED_DATASET" in report.command_steps[1].command_text


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "gate.json", _launch_gate())

    report, outputs = build_and_write_recorded_backtest_command_plan_report(
        recorded_backtest_launch_gate_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["recorded_backtest_command_plan_pack_txt"].read_text(encoding="utf-8")
    commands_csv = outputs["recorded_backtest_commands_csv"].read_text(encoding="utf-8")
    commands_ps1 = outputs["recorded_backtest_manual_commands_ps1"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_BACKTEST_COMMAND_PLAN_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["recorded_backtest_command_plan_pack_json"].exists()
    assert "command_index,command_name,command_text,stage,expected_output,safety_boundary" in commands_csv
    assert "run_existing_one_command_backtest" in commands_csv
    assert "hqe_one_command_backtest_runner.bat" in commands_ps1
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_manual_operator_run"] is True
    assert "hqe_recorded_backtest_command_plan_pack.bat" in combined_docs
    assert "recorded backtest command plan pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module EEEE: 83 modules" in combined_docs
