import json
from pathlib import Path

from src.paper_trading.dashboard_section_registry_pack import (
    build_and_write_dashboard_section_registry_report,
    build_dashboard_section_registry_report,
    safety_notice,
)


CARD_NAMES = [
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


def _card(index, name):
    return {
        "card_index": index,
        "card_name": name,
        "label": name.replace("_", " ").title(),
        "value": "sample",
        "status": "ready",
        "description": f"{name} description",
    }


def _snapshot(status="pass", ready=True, cards=None, issues=None):
    if cards is None:
        cards = [_card(index, name) for index, name in enumerate(CARD_NAMES, start=1)]

    return {
        "status": status,
        "ready_for_future_streamlit_layout": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "card_count": len(cards),
        "dashboard_entry_count": 10,
        "dashboard_existing_entry_count": 10,
        "dashboard_missing_entry_count": 0,
        "completed_total_after_module": 75,
        "phase_2_pending_after_module": 6,
        "full_hqe_product_estimate_after_module": "67-72%",
        "safety_notice": "paper/simulation dashboard overview snapshot pack only",
        "issues": [] if issues is None else issues,
        "overview_cards": cards,
        "dashboard_categories": ["readiness", "mode_config", "mode_run_matrix", "mode_results", "cost_review"],
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_section_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard section registry pack" in notice
    assert "dashboard sections and card routes" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_overview_snapshot_fails(tmp_path):
    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_streamlit_component_scaffold is False
    assert any(issue.code == "dashboard_overview_snapshot_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_overview_snapshot_fails(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_overview_snapshot_pack_invalid_json" for issue in report.issues)


def test_valid_snapshot_creates_sections_and_routes(tmp_path):
    path = _write_json(tmp_path / "snapshot.json", _snapshot())

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    section_names = {section.section_name for section in report.sections}
    routed_cards = {route.card_name for route in report.card_routes}

    assert report.status == "pass"
    assert report.ready_for_future_streamlit_component_scaffold is True
    assert report.section_count == 6
    assert report.card_route_count == 9
    assert report.overview_card_count == 9
    assert {"overview", "progress", "inputs", "mode_evidence", "cost_review", "safety"} <= section_names
    assert set(CARD_NAMES) == routed_cards
    assert report.completed_total_before_module == 75
    assert report.completed_total_after_module == 76
    assert report.phase_2_pending_after_module == 5
    assert report.full_hqe_product_estimate_after_module == "68-73%"


def test_warning_snapshot_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "snapshot.json",
        _snapshot(status="warn", ready=True),
    )

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_overview_snapshot_pack_warn" for issue in report.issues)


def test_warning_snapshot_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "snapshot.json",
        _snapshot(status="warn", ready=True),
    )

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_streamlit_component_scaffold is True


def test_not_ready_snapshot_fails(tmp_path):
    path = _write_json(
        tmp_path / "snapshot.json",
        _snapshot(status="pass", ready=False),
    )

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_overview_snapshot_pack_not_ready" for issue in report.issues)


def test_snapshot_fail_issues_fail_registry(tmp_path):
    path = _write_json(
        tmp_path / "snapshot.json",
        _snapshot(
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

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_overview_snapshot_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_overview_cards_fail(tmp_path):
    cards = [_card(index, name) for index, name in enumerate(CARD_NAMES[:4], start=1)]
    path = _write_json(tmp_path / "snapshot.json", _snapshot(cards=cards))

    report = build_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_overview_cards_missing" for issue in report.issues)


def test_build_and_write_outputs_include_sections_and_routes_csv(tmp_path):
    path = _write_json(tmp_path / "snapshot.json", _snapshot())

    report, outputs = build_and_write_dashboard_section_registry_report(
        dashboard_overview_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_section_registry_pack_txt"].read_text(encoding="utf-8")
    sections_csv = outputs["dashboard_sections_csv"].read_text(encoding="utf-8")
    routes_csv = outputs["dashboard_card_routes_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["dashboard_section_registry_pack_json"].exists()
    assert "section_index,section_name,title,status,purpose" in sections_csv
    assert "route_index,section_name,card_name,label,source_status,route_status" in routes_csv
    assert "progress" in sections_csv
    assert "safety_boundary" in routes_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_streamlit_component_scaffold"] is True


def test_docs_reference_dashboard_section_registry_pack():
    doc_paths = [
        Path("docs/DASHBOARD_SECTION_REGISTRY_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_dashboard_section_registry_pack.bat" in combined_docs
    assert "dashboard section registry pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module XXX: 76 modules" in combined_docs
