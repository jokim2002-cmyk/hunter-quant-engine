import json
from pathlib import Path

from src.paper_trading.paper_improvement_candidate_registry_pack import (
    build_and_write_paper_improvement_candidate_registry_report,
    build_paper_improvement_candidate_registry_report,
    safety_notice,
)


READINESS_ITEMS = [
    "evidence_baseline_freeze",
    "dataset_scope_preservation",
    "ledger_issue_review",
    "metrics_context_preservation",
    "cost_risk_context_preservation",
    "report_language_guard",
    "candidate_improvement_log",
    "regression_test_plan",
    "paper_rerun_boundary",
    "git_output_guard",
]


def _readiness_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "readiness_area": "planning",
        "evidence_source": f"{name}_evidence",
        "readiness_instruction": f"{name} instruction",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _launch(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = READINESS_ITEMS

    improvement_readiness_items = [
        _readiness_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_paper_improvement_readiness": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "improvement_readiness_item_count": len(improvement_readiness_items),
        "phase_4_close_checklist_item_count": 11,
        "close_gate_item_count": 10,
        "report_safety_language_item_count": 10,
        "metrics_context_item_count": 9,
        "ledger_snapshot_item_count": 8,
        "analysis_item_count": 8,
        "review_summary_item_count": 8,
        "presence_check_count": 8,
        "expected_output_count": 8,
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 94,
        "phase_5_pending_after_module": 5,
        "full_hqe_product_estimate_after_module": "86-91%",
        "recommended_next_action": "build candidate registry",
        "safety_notice": "paper/simulation paper improvement readiness launch pack only",
        "issues": [] if issues is None else issues,
        "improvement_readiness_items": improvement_readiness_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_candidate_registry_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper improvement candidate registry pack" in notice
    assert "planning-only improvement candidate registry" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_readiness_launch_fails(tmp_path):
    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_candidate_test_plan is False
    assert any(
        issue.code == "paper_improvement_readiness_launch_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_readiness_launch_fails(tmp_path):
    path = tmp_path / "launch.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_readiness_launch_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_readiness_launch_creates_candidate_registry(tmp_path):
    path = _write_json(tmp_path / "launch.json", _launch())

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    candidate_names = {item.candidate_name for item in report.candidate_registry_items}

    assert report.status == "pass"
    assert report.ready_for_candidate_test_plan is True
    assert report.candidate_registry_item_count == 10
    assert report.improvement_readiness_item_count == 10
    assert report.phase_4_close_checklist_item_count == 11
    assert report.close_gate_item_count == 10
    assert report.report_safety_language_item_count == 10
    assert report.metrics_context_item_count == 9
    assert report.ledger_snapshot_item_count == 8
    assert report.analysis_item_count == 8
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.missing_required_file_count == 0
    assert "baseline_documentation_candidate" in candidate_names
    assert "regression_test_candidate" in candidate_names
    assert "generated_output_git_guard_candidate" in candidate_names
    assert report.completed_total_before_module == 94
    assert report.completed_total_after_module == 95
    assert report.phase_5_pending_after_module == 4
    assert report.full_hqe_product_estimate_after_module == "87-92%"


def test_warning_readiness_launch_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(status="warn", ready=True),
    )

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_readiness_launch_pack_warn"
        for issue in report.issues
    )


def test_warning_readiness_launch_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(status="warn", ready=True),
    )

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_candidate_test_plan is True


def test_not_ready_readiness_launch_fails(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(status="pass", ready=False),
    )

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_readiness_launch_pack_not_ready"
        for issue in report.issues
    )


def test_readiness_launch_fail_issues_fail_candidate_registry(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(
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

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_readiness_launch_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_readiness_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(names=READINESS_ITEMS[:3]),
    )

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_improvement_readiness_items_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(missing_required=2),
    )

    report = build_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_improvement_candidate_registry_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "launch.json", _launch())

    report, outputs = build_and_write_paper_improvement_candidate_registry_report(
        paper_improvement_readiness_launch_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_improvement_candidate_registry_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_improvement_candidate_registry_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_IMPROVEMENT_CANDIDATE_REGISTRY_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_improvement_candidate_registry_pack_json"].exists()
    assert "item_index,candidate_name,candidate_area,evidence_source,candidate_instruction,implementation_status,safety_boundary" in items_csv
    assert "baseline_documentation_candidate" in items_csv
    assert "generated_output_git_guard_candidate" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_candidate_test_plan"] is True
    assert "hqe_paper_improvement_candidate_registry_pack.bat" in combined_docs
    assert "paper improvement candidate registry pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module QQQQ: 95 modules" in combined_docs
