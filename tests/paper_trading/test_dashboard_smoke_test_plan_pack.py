import json
from pathlib import Path

from src.paper_trading.dashboard_smoke_test_plan_pack import (
    build_and_write_dashboard_smoke_test_plan_report,
    build_dashboard_smoke_test_plan_report,
    safety_notice,
)


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


def _page(index, name):
    return {
        "page_index": index,
        "page_name": name,
        "title": name.replace("_", " ").title(),
        "sections": ["overview", "safety"],
        "status": "ready",
        "purpose": f"{name} purpose",
    }


def _shell(status="pass", ready=True, pages=None, components=None, sections=None, issues=None):
    if pages is None:
        pages = [_page(index, name) for index, name in enumerate(PAGES, start=1)]
    if components is None:
        components = COMPONENTS
    if sections is None:
        sections = SECTIONS

    return {
        "status": status,
        "ready_for_future_dashboard_smoke_test": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "page_count": len(pages),
        "component_count": len(components),
        "section_count": len(sections),
        "completed_total_after_module": 78,
        "phase_2_pending_after_module": 3,
        "full_hqe_product_estimate_after_module": "70-75%",
        "safety_notice": "paper/simulation dashboard app shell pack only",
        "issues": [] if issues is None else issues,
        "pages": pages,
        "component_names": components,
        "section_names": sections,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_smoke_test_plan_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard smoke test plan pack" in notice
    assert "future dashboard smoke-test steps" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_app_shell_fails(tmp_path):
    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_streamlit_dry_run is False
    assert any(issue.code == "dashboard_app_shell_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_app_shell_fails(tmp_path):
    path = tmp_path / "shell.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_app_shell_pack_invalid_json" for issue in report.issues)


def test_valid_app_shell_creates_smoke_test_plan(tmp_path):
    path = _write_json(tmp_path / "shell.json", _shell())

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    step_names = {step.step_name for step in report.smoke_steps}

    assert report.status == "pass"
    assert report.ready_for_future_streamlit_dry_run is True
    assert report.smoke_step_count == 6
    assert report.page_count == 3
    assert report.component_count == 6
    assert report.section_count == 6
    assert "verify_safety_boundary" in step_names
    assert "verify_no_execution_hooks" in step_names
    assert report.completed_total_before_module == 78
    assert report.completed_total_after_module == 79
    assert report.phase_2_pending_after_module == 2
    assert report.full_hqe_product_estimate_after_module == "71-76%"


def test_warning_app_shell_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "shell.json",
        _shell(status="warn", ready=True),
    )

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_app_shell_pack_warn" for issue in report.issues)


def test_warning_app_shell_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "shell.json",
        _shell(status="warn", ready=True),
    )

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_streamlit_dry_run is True


def test_not_ready_app_shell_fails(tmp_path):
    path = _write_json(
        tmp_path / "shell.json",
        _shell(status="pass", ready=False),
    )

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_app_shell_pack_not_ready" for issue in report.issues)


def test_app_shell_fail_issues_fail_smoke_plan(tmp_path):
    path = _write_json(
        tmp_path / "shell.json",
        _shell(
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

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_app_shell_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_pages_fail(tmp_path):
    pages = [_page(1, "overview")]
    path = _write_json(tmp_path / "shell.json", _shell(pages=pages))

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_smoke_test_pages_missing" for issue in report.issues)


def test_missing_required_components_fail(tmp_path):
    path = _write_json(
        tmp_path / "shell.json",
        _shell(components=COMPONENTS[:3]),
    )

    report = build_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_smoke_test_components_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "shell.json", _shell())

    report, outputs = build_and_write_dashboard_smoke_test_plan_report(
        dashboard_app_shell_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_smoke_test_plan_pack_txt"].read_text(encoding="utf-8")
    steps_csv = outputs["dashboard_smoke_test_steps_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/DASHBOARD_SMOKE_TEST_PLAN_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["dashboard_smoke_test_plan_pack_json"].exists()
    assert "step_index,step_name,page_name,expected_result,status,safety_check" in steps_csv
    assert "verify_safety_boundary" in steps_csv
    assert "verify_no_execution_hooks" in steps_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_streamlit_dry_run"] is True
    assert "hqe_dashboard_smoke_test_plan_pack.bat" in combined_docs
    assert "dashboard smoke test plan pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module AAAA: 79 modules" in combined_docs
