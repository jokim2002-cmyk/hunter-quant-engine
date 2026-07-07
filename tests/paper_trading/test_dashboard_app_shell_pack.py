import json
from pathlib import Path

from src.paper_trading.dashboard_app_shell_pack import (
    build_and_write_dashboard_app_shell_report,
    build_dashboard_app_shell_report,
    safety_notice,
)


COMPONENTS = [
    "overview_header",
    "progress_card_grid",
    "input_evidence_table",
    "mode_evidence_table",
    "cost_review_table",
    "safety_boundary_panel",
]
SECTIONS = ["overview", "progress", "inputs", "mode_evidence", "cost_review", "safety"]


def _component(index, name):
    section = "overview"
    if name == "progress_card_grid":
        section = "progress"
    if name == "input_evidence_table":
        section = "inputs"
    if name == "mode_evidence_table":
        section = "mode_evidence"
    if name == "cost_review_table":
        section = "cost_review"
    if name == "safety_boundary_panel":
        section = "safety"

    return {
        "component_index": index,
        "component_name": name,
        "section_name": section,
        "component_type": "table",
        "source_reference": f"{name}.json",
        "status": "ready",
        "implementation_note": f"{name} note",
    }


def _scaffold(status="pass", ready=True, components=None, sections=None, issues=None):
    if components is None:
        components = [_component(index, name) for index, name in enumerate(COMPONENTS, start=1)]
    if sections is None:
        sections = SECTIONS

    return {
        "status": status,
        "ready_for_future_streamlit_app_shell": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "component_count": len(components),
        "section_count": len(sections),
        "card_route_count": 9,
        "completed_total_after_module": 77,
        "phase_2_pending_after_module": 4,
        "full_hqe_product_estimate_after_module": "69-74%",
        "safety_notice": "paper/simulation dashboard component scaffold pack only",
        "issues": [] if issues is None else issues,
        "components": components,
        "section_names": sections,
        "route_card_names": [
            "project_progress",
            "v1_status",
            "phase_1_status",
            "phase_2_status",
            "dashboard_inputs",
            "existing_dashboard_inputs",
            "missing_dashboard_inputs",
            "selected_dataset",
            "safety_boundary",
        ],
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_app_shell_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard app shell pack" in notice
    assert "future streamlit app shell template" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_component_scaffold_fails(tmp_path):
    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_dashboard_smoke_test is False
    assert any(issue.code == "dashboard_component_scaffold_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_component_scaffold_fails(tmp_path):
    path = tmp_path / "scaffold.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_component_scaffold_pack_invalid_json" for issue in report.issues)


def test_valid_component_scaffold_creates_app_shell_pages(tmp_path):
    path = _write_json(tmp_path / "scaffold.json", _scaffold())

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    page_names = {page.page_name for page in report.pages}

    assert report.status == "pass"
    assert report.ready_for_future_dashboard_smoke_test is True
    assert report.page_count == 3
    assert page_names == {"overview", "evidence", "cost_review"}
    assert report.component_count == 6
    assert report.section_count == 6
    assert report.completed_total_before_module == 77
    assert report.completed_total_after_module == 78
    assert report.phase_2_pending_after_module == 3
    assert report.full_hqe_product_estimate_after_module == "70-75%"


def test_warning_component_scaffold_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "scaffold.json",
        _scaffold(status="warn", ready=True),
    )

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_component_scaffold_pack_warn" for issue in report.issues)


def test_warning_component_scaffold_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "scaffold.json",
        _scaffold(status="warn", ready=True),
    )

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_dashboard_smoke_test is True


def test_not_ready_component_scaffold_fails(tmp_path):
    path = _write_json(
        tmp_path / "scaffold.json",
        _scaffold(status="pass", ready=False),
    )

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_component_scaffold_pack_not_ready" for issue in report.issues)


def test_component_scaffold_fail_issues_fail_app_shell(tmp_path):
    path = _write_json(
        tmp_path / "scaffold.json",
        _scaffold(
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

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_component_scaffold_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_components_fail(tmp_path):
    components = [_component(index, name) for index, name in enumerate(COMPONENTS[:3], start=1)]
    path = _write_json(tmp_path / "scaffold.json", _scaffold(components=components))

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_app_shell_components_missing" for issue in report.issues)


def test_missing_required_sections_fail(tmp_path):
    path = _write_json(
        tmp_path / "scaffold.json",
        _scaffold(sections=["overview", "progress", "inputs"]),
    )

    report = build_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_app_shell_sections_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "scaffold.json", _scaffold())

    report, outputs = build_and_write_dashboard_app_shell_report(
        dashboard_component_scaffold_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_app_shell_pack_txt"].read_text(encoding="utf-8")
    pages_csv = outputs["dashboard_app_pages_csv"].read_text(encoding="utf-8")
    template_py = outputs["dashboard_app_shell_template_py"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/DASHBOARD_APP_SHELL_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["dashboard_app_shell_pack_json"].exists()
    assert "page_index,page_name,title,sections,status,purpose" in pages_csv
    assert "overview" in pages_csv
    assert "cost_review" in pages_csv
    assert "describe_app_shell" in template_py
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_dashboard_smoke_test"] is True
    assert "hqe_dashboard_app_shell_pack.bat" in combined_docs
    assert "dashboard app shell pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module ZZZ: 78 modules" in combined_docs
