import json
from pathlib import Path

from src.paper_trading.dashboard_overview_snapshot_pack import (
    build_and_write_dashboard_overview_snapshot_report,
    build_dashboard_overview_snapshot_report,
    safety_notice,
)


CATEGORIES = [
    "readiness",
    "dataset",
    "run_order",
    "verification",
    "review",
    "tuning",
    "mode_config",
    "mode_run_matrix",
    "mode_results",
    "cost_review",
]


def _entry(index, category):
    return {
        "entry_index": index,
        "entry_name": f"{category}_entry",
        "category": category,
        "path": f"reports/{category}.json",
        "exists": True,
        "required_for_dashboard": category == "readiness",
        "description": f"{category} evidence",
    }


def _index_pack(status="pass", ready=True, categories=None, issues=None):
    if categories is None:
        categories = CATEGORIES

    return {
        "status": status,
        "ready_for_future_streamlit_dashboard": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "entry_count": len(categories),
        "existing_entry_count": len(categories),
        "missing_entry_count": 0,
        "completed_total_after_module": 74,
        "phase_2_pending_after_module": 7,
        "full_hqe_product_estimate_after_module": "66-71%",
        "safety_notice": "paper/simulation dashboard input index pack only",
        "issues": [] if issues is None else issues,
        "entries": [_entry(index, category) for index, category in enumerate(categories, start=1)],
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_overview_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard overview snapshot pack" in notice
    assert "static dashboard overview cards" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_dashboard_input_index_fails(tmp_path):
    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_streamlit_layout is False
    assert any(issue.code == "dashboard_input_index_pack_missing" for issue in report.issues)


def test_invalid_json_dashboard_input_index_fails(tmp_path):
    path = tmp_path / "index.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_input_index_pack_invalid_json" for issue in report.issues)


def test_valid_dashboard_input_index_creates_overview_cards(tmp_path):
    path = _write_json(tmp_path / "index.json", _index_pack())

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    card_names = {card.card_name for card in report.overview_cards}

    assert report.status == "pass"
    assert report.ready_for_future_streamlit_layout is True
    assert report.card_count == 9
    assert report.dashboard_entry_count == 10
    assert "project_progress" in card_names
    assert "safety_boundary" in card_names
    assert report.completed_total_before_module == 74
    assert report.completed_total_after_module == 75
    assert report.phase_2_pending_after_module == 6
    assert report.full_hqe_product_estimate_after_module == "67-72%"


def test_warning_dashboard_input_index_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "index.json",
        _index_pack(status="warn", ready=True),
    )

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_input_index_pack_warn" for issue in report.issues)


def test_warning_dashboard_input_index_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "index.json",
        _index_pack(status="warn", ready=True),
    )

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_streamlit_layout is True


def test_not_ready_dashboard_input_index_fails(tmp_path):
    path = _write_json(
        tmp_path / "index.json",
        _index_pack(status="pass", ready=False),
    )

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_input_index_pack_not_ready" for issue in report.issues)


def test_index_fail_issues_fail_snapshot(tmp_path):
    path = _write_json(
        tmp_path / "index.json",
        _index_pack(
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

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "dashboard_input_index_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_dashboard_categories_fail(tmp_path):
    path = _write_json(
        tmp_path / "index.json",
        _index_pack(categories=["readiness", "dataset", "review"]),
    )

    report = build_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_dashboard_overview_categories_missing" for issue in report.issues)


def test_build_and_write_outputs_include_cards_csv(tmp_path):
    path = _write_json(tmp_path / "index.json", _index_pack())

    report, outputs = build_and_write_dashboard_overview_snapshot_report(
        dashboard_input_index_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_overview_snapshot_pack_txt"].read_text(encoding="utf-8")
    cards_csv = outputs["dashboard_overview_cards_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["dashboard_overview_snapshot_pack_json"].exists()
    assert "card_index,card_name,label,value,status,description" in cards_csv
    assert "project_progress" in cards_csv
    assert "safety_boundary" in cards_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_streamlit_layout"] is True


def test_docs_reference_dashboard_overview_snapshot_pack():
    doc_paths = [
        Path("docs/DASHBOARD_OVERVIEW_SNAPSHOT_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_dashboard_overview_snapshot_pack.bat" in combined_docs
    assert "dashboard overview snapshot pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module WWW: 75 modules" in combined_docs
