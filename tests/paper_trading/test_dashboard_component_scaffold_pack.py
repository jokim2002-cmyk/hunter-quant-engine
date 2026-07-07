import json
from pathlib import Path

from src.paper_trading.dashboard_component_scaffold_pack import (
    build_and_write_dashboard_component_scaffold_report,
    build_dashboard_component_scaffold_report,
    safety_notice,
)


SECTIONS = ["overview", "progress", "inputs", "mode_evidence", "cost_review", "safety"]
ROUTE_CARDS = [
    "project_progress",
    "v1_status",
    "phase_1_status",
    "phase_2_status",
    "dashboard_inputs",
    "existing_dashboard_inputs",
    "missing_dashboard_inputs",
    "selected_dataset",
    "safety_boundary",
]


def _section(index, name):
    return {
        "section_index": index,
        "section_name": name,
        "title": name.replace("_", " ").title(),
        "status": "ready",
        "purpose": f"{name} purpose",
    }


def _route(index, card_name):
    section = "progress"
    if "input" in card_name:
        section = "inputs"
    if card_name == "selected_dataset":
        section = "overview"
    if card_name == "safety_boundary":
        section = "safety"

    return {
        "route_index": index,
        "section_name": section,
        "card_name": card_name,
        "label": card_name.replace("_", " ").title(),
        "source_status": "ready",
        "route_status": "ready",
    }


def _registry(status="pass", ready=True, sections=None, routes=None, issues=None):
    if sections is None:
        sections = [_section(index, name) for index, name in enumerate(SECTIONS, start=1)]
    if routes is None:
        routes = [_route(index, name) for index, name in enumerate(ROUTE_CARDS, start=1)]

    return {
        "status": status,
        "ready_for_future_streamlit_component_scaffold": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "section_count": len(sections),
        "card_route_count": len(routes),
        "overview_card_count": len(routes),
        "completed_total_after_module": 76,
        "phase_2_pending_after_module": 5,
        "full_hqe_product_estimate_after_module": "68-73%",
        "safety_notice": "paper/simulation dashboard section registry pack only",
        "issues": [] if issues is None else issues,
        "sections": sections,
        "card_routes": routes,
        "overview_card_names": ROUTE_CARDS,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_component_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard component scaffold pack" in notice
    assert "future streamlit component definitions" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_section_registry_fails(tmp_path):
    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_streamlit_app_shell is False
    assert any(issue.code == "dashboard_section_registry_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_section_registry_fails(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_section_registry_pack_invalid_json" for issue in report.issues)


def test_valid_registry_creates_component_scaffold(tmp_path):
    path = _write_json(tmp_path / "registry.json", _registry())

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    component_names = {component.component_name for component in report.components}

    assert report.status == "pass"
    assert report.ready_for_future_streamlit_app_shell is True
    assert report.component_count == 6
    assert report.section_count == 6
    assert report.card_route_count == 9
    assert "overview_header" in component_names
    assert "safety_boundary_panel" in component_names
    assert report.completed_total_before_module == 76
    assert report.completed_total_after_module == 77
    assert report.phase_2_pending_after_module == 4
    assert report.full_hqe_product_estimate_after_module == "69-74%"


def test_warning_registry_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(status="warn", ready=True),
    )

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_section_registry_pack_warn" for issue in report.issues)


def test_warning_registry_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(status="warn", ready=True),
    )

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_streamlit_app_shell is True


def test_not_ready_registry_fails(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(status="pass", ready=False),
    )

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_section_registry_pack_not_ready" for issue in report.issues)


def test_registry_fail_issues_fail_scaffold(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(
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

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_section_registry_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_sections_fail(tmp_path):
    sections = [_section(index, name) for index, name in enumerate(["overview", "progress"], start=1)]
    path = _write_json(tmp_path / "registry.json", _registry(sections=sections))

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_component_sections_missing" for issue in report.issues)


def test_missing_required_card_routes_fail(tmp_path):
    routes = [_route(index, name) for index, name in enumerate(ROUTE_CARDS[:4], start=1)]
    path = _write_json(tmp_path / "registry.json", _registry(routes=routes))

    report = build_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_component_card_routes_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "registry.json", _registry())

    report, outputs = build_and_write_dashboard_component_scaffold_report(
        dashboard_section_registry_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_component_scaffold_pack_txt"].read_text(encoding="utf-8")
    components_csv = outputs["dashboard_components_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/DASHBOARD_COMPONENT_SCAFFOLD_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["dashboard_component_scaffold_pack_json"].exists()
    assert "component_index,component_name,section_name,component_type,source_reference,status,implementation_note" in components_csv
    assert "overview_header" in components_csv
    assert "safety_boundary_panel" in components_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_streamlit_app_shell"] is True
    assert "hqe_dashboard_component_scaffold_pack.bat" in combined_docs
    assert "dashboard component scaffold pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module YYY: 77 modules" in combined_docs
