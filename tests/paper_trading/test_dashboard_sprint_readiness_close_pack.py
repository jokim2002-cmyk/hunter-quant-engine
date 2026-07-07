import json
from pathlib import Path

from src.paper_trading.dashboard_sprint_readiness_close_pack import (
    build_and_write_dashboard_sprint_readiness_close_report,
    build_dashboard_sprint_readiness_close_report,
    safety_notice,
)


VALIDATION_ITEMS = [
    "plain_python_template_validation",
    "page_registry_validation",
    "component_registry_validation",
    "section_registry_validation",
    "smoke_step_validation",
    "safety_boundary_validation",
    "profitability_claim_guard_validation",
]
SMOKE_STEPS = [
    "load_app_shell_template",
    "verify_overview_page",
    "verify_evidence_page",
    "verify_cost_review_page",
    "verify_safety_boundary",
    "verify_no_execution_hooks",
]
PAGES = ["overview", "evidence", "cost_review"]
COMPONENTS = [
    "overview_header",
    "progress_card_grid",
    "input_evidence_table",
    "mode_evidence_table",
    "cost_review_table",
    "safety_boundary_panel",
]
SECTIONS = ["overview", "progress", "inputs", "mode_evidence", "cost_review", "safety"]


def _item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "validation_area": "safety",
        "expected_result": f"{name} expected",
        "status": "planned",
        "safety_boundary": f"{name} safety",
    }


def _validation(
    status="pass",
    ready=True,
    validation_items=None,
    smoke_steps=None,
    pages=None,
    components=None,
    sections=None,
    issues=None,
):
    if validation_items is None:
        validation_items = [
            _item(index, name)
            for index, name in enumerate(VALIDATION_ITEMS, start=1)
        ]
    if smoke_steps is None:
        smoke_steps = SMOKE_STEPS
    if pages is None:
        pages = PAGES
    if components is None:
        components = COMPONENTS
    if sections is None:
        sections = SECTIONS

    return {
        "status": status,
        "ready_for_dashboard_sprint_close": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "validation_item_count": len(validation_items),
        "smoke_step_count": len(smoke_steps),
        "page_count": len(pages),
        "component_count": len(components),
        "section_count": len(sections),
        "completed_total_after_module": 80,
        "phase_2_pending_after_module": 1,
        "full_hqe_product_estimate_after_module": "72-77%",
        "safety_notice": "paper/simulation dashboard dry run validation pack only",
        "issues": [] if issues is None else issues,
        "validation_items": validation_items,
        "smoke_step_names": smoke_steps,
        "page_names": pages,
        "component_names": components,
        "section_names": sections,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_sprint_close_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard sprint readiness close pack" in notice
    assert "closes the dashboard sprint" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_dry_run_validation_fails(tmp_path):
    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.dashboard_sprint_closed is False
    assert any(issue.code == "dashboard_dry_run_validation_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_dry_run_validation_fails(tmp_path):
    path = tmp_path / "validation.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_dry_run_validation_pack_invalid_json" for issue in report.issues)


def test_valid_dashboard_dry_run_validation_closes_dashboard_sprint(tmp_path):
    path = _write_json(tmp_path / "validation.json", _validation())

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.dashboard_sprint_closed is True
    assert report.ready_for_recorded_backtest_review_workflow is True
    assert report.checklist_item_count == 8
    assert report.validation_item_count == 7
    assert report.completed_total_before_module == 80
    assert report.completed_total_after_module == 81
    assert report.phase_2_pending_after_module == 0
    assert report.full_hqe_product_estimate_after_module == "73-78%"


def test_warning_dashboard_dry_run_validation_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "validation.json",
        _validation(status="warn", ready=True),
    )

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_dry_run_validation_pack_warn" for issue in report.issues)


def test_warning_dashboard_dry_run_validation_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "validation.json",
        _validation(status="warn", ready=True),
    )

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.dashboard_sprint_closed is True
    assert report.ready_for_recorded_backtest_review_workflow is True


def test_not_ready_dashboard_dry_run_validation_fails(tmp_path):
    path = _write_json(
        tmp_path / "validation.json",
        _validation(status="pass", ready=False),
    )

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_dry_run_validation_pack_not_ready" for issue in report.issues)


def test_dry_run_validation_fail_issues_fail_close(tmp_path):
    path = _write_json(
        tmp_path / "validation.json",
        _validation(
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

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_dry_run_validation_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_validation_items_and_smoke_steps_fail(tmp_path):
    validation_items = [
        _item(index, name)
        for index, name in enumerate(VALIDATION_ITEMS[:3], start=1)
    ]
    path = _write_json(
        tmp_path / "validation.json",
        _validation(validation_items=validation_items, smoke_steps=SMOKE_STEPS[:3]),
    )

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    codes = {issue.code for issue in report.issues}

    assert report.status == "fail"
    assert "required_dashboard_close_validation_items_missing" in codes
    assert "required_dashboard_close_smoke_steps_missing" in codes


def test_missing_required_pages_components_and_sections_fail(tmp_path):
    path = _write_json(
        tmp_path / "validation.json",
        _validation(
            pages=["overview"],
            components=COMPONENTS[:2],
            sections=["overview", "progress"],
        ),
    )

    report = build_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    codes = {issue.code for issue in report.issues}

    assert report.status == "fail"
    assert "required_dashboard_close_pages_missing" in codes
    assert "required_dashboard_close_components_missing" in codes
    assert "required_dashboard_close_sections_missing" in codes


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "validation.json", _validation())

    report, outputs = build_and_write_dashboard_sprint_readiness_close_report(
        dashboard_dry_run_validation_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_sprint_readiness_close_pack_txt"].read_text(encoding="utf-8")
    checklist_csv = outputs["dashboard_sprint_close_checklist_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/DASHBOARD_SPRINT_READINESS_CLOSE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["dashboard_sprint_readiness_close_pack_json"].exists()
    assert "item_index,item_name,status,evidence,next_instruction" in checklist_csv
    assert "dashboard_dry_run_validation" in checklist_csv
    assert "safety_boundary" in checklist_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["dashboard_sprint_closed"] is True
    assert manifest["phase_2_pending_after_module"] == 0
    assert "hqe_dashboard_sprint_readiness_close_pack.bat" in combined_docs
    assert "dashboard sprint readiness close pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module CCCC: 81 modules" in combined_docs
