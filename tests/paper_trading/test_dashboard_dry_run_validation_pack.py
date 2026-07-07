import json
from pathlib import Path

from src.paper_trading.dashboard_dry_run_validation_pack import (
    build_and_write_dashboard_dry_run_validation_report,
    build_dashboard_dry_run_validation_report,
    safety_notice,
)


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


def _step(index, name):
    return {
        "step_index": index,
        "step_name": name,
        "page_name": "overview",
        "expected_result": f"{name} expected",
        "status": "planned",
        "safety_check": f"{name} safety",
    }


def _plan(
    status="pass",
    ready=True,
    smoke_steps=None,
    pages=None,
    components=None,
    sections=None,
    issues=None,
):
    if smoke_steps is None:
        smoke_steps = [_step(index, name) for index, name in enumerate(SMOKE_STEPS, start=1)]
    if pages is None:
        pages = PAGES
    if components is None:
        components = COMPONENTS
    if sections is None:
        sections = SECTIONS

    return {
        "status": status,
        "ready_for_future_streamlit_dry_run": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "smoke_step_count": len(smoke_steps),
        "page_count": len(pages),
        "component_count": len(components),
        "section_count": len(sections),
        "completed_total_after_module": 79,
        "phase_2_pending_after_module": 2,
        "full_hqe_product_estimate_after_module": "71-76%",
        "safety_notice": "paper/simulation dashboard smoke test plan pack only",
        "issues": [] if issues is None else issues,
        "smoke_steps": smoke_steps,
        "page_names": pages,
        "component_names": components,
        "section_names": sections,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_dry_run_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard dry run validation pack" in notice
    assert "future dashboard dry-run validation items" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_smoke_test_plan_fails(tmp_path):
    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_dashboard_sprint_close is False
    assert any(issue.code == "dashboard_smoke_test_plan_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_smoke_test_plan_fails(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_smoke_test_plan_pack_invalid_json" for issue in report.issues)


def test_valid_smoke_test_plan_creates_dry_run_validation(tmp_path):
    path = _write_json(tmp_path / "plan.json", _plan())

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    item_names = {item.item_name for item in report.validation_items}

    assert report.status == "pass"
    assert report.ready_for_dashboard_sprint_close is True
    assert report.validation_item_count == 7
    assert report.smoke_step_count == 6
    assert report.page_count == 3
    assert report.component_count == 6
    assert report.section_count == 6
    assert "safety_boundary_validation" in item_names
    assert "profitability_claim_guard_validation" in item_names
    assert report.completed_total_before_module == 79
    assert report.completed_total_after_module == 80
    assert report.phase_2_pending_after_module == 1
    assert report.full_hqe_product_estimate_after_module == "72-77%"


def test_warning_smoke_test_plan_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _plan(status="warn", ready=True),
    )

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_smoke_test_plan_pack_warn" for issue in report.issues)


def test_warning_smoke_test_plan_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _plan(status="warn", ready=True),
    )

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_dashboard_sprint_close is True


def test_not_ready_smoke_test_plan_fails(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _plan(status="pass", ready=False),
    )

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_smoke_test_plan_pack_not_ready" for issue in report.issues)


def test_smoke_test_plan_fail_issues_fail_validation(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _plan(
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

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_smoke_test_plan_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_smoke_steps_fail(tmp_path):
    smoke_steps = [_step(index, name) for index, name in enumerate(SMOKE_STEPS[:3], start=1)]
    path = _write_json(tmp_path / "plan.json", _plan(smoke_steps=smoke_steps))

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_dry_run_smoke_steps_missing" for issue in report.issues)


def test_missing_required_pages_components_and_sections_fail(tmp_path):
    path = _write_json(
        tmp_path / "plan.json",
        _plan(
            pages=["overview"],
            components=COMPONENTS[:2],
            sections=["overview", "progress"],
        ),
    )

    report = build_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    codes = {issue.code for issue in report.issues}

    assert report.status == "fail"
    assert "required_dashboard_dry_run_pages_missing" in codes
    assert "required_dashboard_dry_run_components_missing" in codes
    assert "required_dashboard_dry_run_sections_missing" in codes


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "plan.json", _plan())

    report, outputs = build_and_write_dashboard_dry_run_validation_report(
        dashboard_smoke_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_dry_run_validation_pack_txt"].read_text(encoding="utf-8")
    validation_csv = outputs["dashboard_dry_run_validation_items_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/DASHBOARD_DRY_RUN_VALIDATION_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["dashboard_dry_run_validation_pack_json"].exists()
    assert "item_index,item_name,validation_area,expected_result,status,safety_boundary" in validation_csv
    assert "safety_boundary_validation" in validation_csv
    assert "profitability_claim_guard_validation" in validation_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_dashboard_sprint_close"] is True
    assert "hqe_dashboard_dry_run_validation_pack.bat" in combined_docs
    assert "dashboard dry run validation pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module BBBB: 80 modules" in combined_docs
