import json
from pathlib import Path

from src.paper_trading.recorded_backtest_launch_gate_pack import (
    build_and_write_recorded_backtest_launch_gate_report,
    build_recorded_backtest_launch_gate_report,
    safety_notice,
)


CHECKLIST_ITEMS = [
    "dashboard_input_index",
    "dashboard_overview_snapshot",
    "dashboard_section_registry",
    "dashboard_component_scaffold",
    "dashboard_app_shell",
    "dashboard_smoke_test_plan",
    "dashboard_dry_run_validation",
    "safety_boundary",
]


def _checklist_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "status": "closed",
        "evidence": f"{name} evidence",
        "next_instruction": f"{name} next",
    }


def _close_pack(status="pass", closed=True, ready=True, checklist=None, issues=None):
    if checklist is None:
        checklist = [
            _checklist_item(index, name)
            for index, name in enumerate(CHECKLIST_ITEMS, start=1)
        ]

    return {
        "status": status,
        "dashboard_sprint_closed": closed,
        "ready_for_recorded_backtest_review_workflow": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "checklist_item_count": len(checklist),
        "validation_item_count": 7,
        "completed_total_after_module": 81,
        "phase_2_pending_after_module": 0,
        "full_hqe_product_estimate_after_module": "73-78%",
        "recommended_next_phase": "recorded-data paper backtest review workflow",
        "safety_notice": "paper/simulation dashboard sprint readiness close pack only",
        "issues": [] if issues is None else issues,
        "checklist": checklist,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_recorded_backtest_launch_gate_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation recorded backtest launch gate pack" in notice
    assert "recorded-data paper backtest review workflow" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_sprint_close_fails(tmp_path):
    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_manual_recorded_backtest_run is False
    assert any(issue.code == "dashboard_sprint_readiness_close_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_sprint_close_fails(tmp_path):
    path = tmp_path / "close.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_sprint_readiness_close_pack_invalid_json" for issue in report.issues)


def test_valid_dashboard_sprint_close_creates_launch_gate(tmp_path):
    path = _write_json(tmp_path / "close.json", _close_pack())

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    step_names = {step.step_name for step in report.launch_steps}

    assert report.status == "pass"
    assert report.ready_for_manual_recorded_backtest_run is True
    assert report.launch_step_count == 7
    assert report.dashboard_close_checklist_item_count == 8
    assert "run_recorded_backtest_manually" in step_names
    assert "verify_outputs_after_run" in step_names
    assert report.completed_total_before_module == 81
    assert report.completed_total_after_module == 82
    assert report.phase_3_pending_after_module == 5
    assert report.full_hqe_product_estimate_after_module == "74-79%"


def test_warning_dashboard_sprint_close_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="warn", closed=True, ready=True),
    )

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_sprint_readiness_close_pack_warn" for issue in report.issues)


def test_warning_dashboard_sprint_close_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="warn", closed=True, ready=True),
    )

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_manual_recorded_backtest_run is True


def test_dashboard_sprint_not_closed_fails(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="pass", closed=False, ready=True),
    )

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_sprint_not_closed" for issue in report.issues)


def test_dashboard_sprint_not_ready_for_recorded_backtest_review_fails(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="pass", closed=True, ready=False),
    )

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "dashboard_sprint_not_ready_for_recorded_backtest_review"
        for issue in report.issues
    )


def test_dashboard_sprint_close_fail_issues_fail_launch_gate(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(
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

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_sprint_close_contains_fail_issues" for issue in report.issues)


def test_missing_required_dashboard_close_checklist_items_fail(tmp_path):
    checklist = [
        _checklist_item(index, name)
        for index, name in enumerate(CHECKLIST_ITEMS[:3], start=1)
    ]
    path = _write_json(tmp_path / "close.json", _close_pack(checklist=checklist))

    report = build_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_close_checklist_items_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "close.json", _close_pack())

    report, outputs = build_and_write_recorded_backtest_launch_gate_report(
        dashboard_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["recorded_backtest_launch_gate_pack_txt"].read_text(encoding="utf-8")
    steps_csv = outputs["recorded_backtest_launch_steps_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_BACKTEST_LAUNCH_GATE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["recorded_backtest_launch_gate_pack_json"].exists()
    assert "step_index,step_name,stage,operator_action,expected_result,safety_boundary" in steps_csv
    assert "run_recorded_backtest_manually" in steps_csv
    assert "verify_outputs_after_run" in steps_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_manual_recorded_backtest_run"] is True
    assert "hqe_recorded_backtest_launch_gate_pack.bat" in combined_docs
    assert "recorded backtest launch gate pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module DDDD: 82 modules" in combined_docs
