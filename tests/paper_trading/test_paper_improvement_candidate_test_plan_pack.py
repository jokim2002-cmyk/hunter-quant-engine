import json
from pathlib import Path

from src.paper_trading.paper_improvement_candidate_test_plan_pack import (
    build_and_write_paper_improvement_candidate_test_plan_report,
    build_paper_improvement_candidate_test_plan_report,
    safety_notice,
)


CANDIDATES = [
    "baseline_documentation_candidate",
    "dataset_scope_review_candidate",
    "ledger_quality_review_candidate",
    "direction_mapping_review_candidate",
    "metrics_context_review_candidate",
    "cost_risk_note_candidate",
    "report_language_guard_candidate",
    "regression_test_candidate",
    "paper_rerun_candidate",
    "generated_output_git_guard_candidate",
]


def _candidate(index, name):
    return {
        "item_index": index,
        "candidate_name": name,
        "candidate_area": "planning",
        "evidence_source": f"{name}_evidence",
        "candidate_instruction": f"{name} instruction",
        "implementation_status": "planning_only",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _registry(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = CANDIDATES

    candidate_registry_items = [
        _candidate(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_candidate_test_plan": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "candidate_registry_item_count": len(candidate_registry_items),
        "improvement_readiness_item_count": 10,
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
        "completed_total_after_module": 95,
        "phase_5_pending_after_module": 4,
        "full_hqe_product_estimate_after_module": "87-92%",
        "recommended_next_action": "build candidate test plan",
        "safety_notice": "paper/simulation paper improvement candidate registry pack only",
        "issues": [] if issues is None else issues,
        "candidate_registry_items": candidate_registry_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_candidate_test_plan_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper improvement candidate test plan pack" in notice
    assert "planning-only test plan items" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_candidate_registry_fails(tmp_path):
    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_paper_rerun_readiness_gate is False
    assert any(
        issue.code == "paper_improvement_candidate_registry_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_candidate_registry_fails(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_registry_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_candidate_registry_creates_test_plan(tmp_path):
    path = _write_json(tmp_path / "registry.json", _registry())

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    test_plan_names = {item.test_plan_name for item in report.test_plan_items}

    assert report.status == "pass"
    assert report.ready_for_paper_rerun_readiness_gate is True
    assert report.test_plan_item_count == 10
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
    assert "baseline_documentation_test_plan" in test_plan_names
    assert "report_language_guard_test_plan" in test_plan_names
    assert "generated_output_git_guard_test_plan" in test_plan_names
    assert report.completed_total_before_module == 95
    assert report.completed_total_after_module == 96
    assert report.phase_5_pending_after_module == 3
    assert report.full_hqe_product_estimate_after_module == "88-93%"


def test_warning_candidate_registry_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(status="warn", ready=True),
    )

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_registry_pack_warn"
        for issue in report.issues
    )


def test_warning_candidate_registry_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(status="warn", ready=True),
    )

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_paper_rerun_readiness_gate is True


def test_not_ready_candidate_registry_fails(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(status="pass", ready=False),
    )

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_registry_pack_not_ready"
        for issue in report.issues
    )


def test_candidate_registry_fail_issues_fail_test_plan(tmp_path):
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

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_registry_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_candidates_fail(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(names=CANDIDATES[:3]),
    )

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_improvement_candidates_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "registry.json",
        _registry(missing_required=2),
    )

    report = build_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_improvement_candidate_test_plan_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "registry.json", _registry())

    report, outputs = build_and_write_paper_improvement_candidate_test_plan_report(
        paper_improvement_candidate_registry_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_improvement_candidate_test_plan_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_improvement_candidate_test_plan_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_IMPROVEMENT_CANDIDATE_TEST_PLAN_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_improvement_candidate_test_plan_pack_json"].exists()
    assert "item_index,test_plan_name,test_area,evidence_source,test_instruction,required_before_status,safety_boundary" in items_csv
    assert "baseline_documentation_test_plan" in items_csv
    assert "generated_output_git_guard_test_plan" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_paper_rerun_readiness_gate"] is True
    assert "hqe_paper_improvement_candidate_test_plan_pack.bat" in combined_docs
    assert "paper improvement candidate test plan pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module RRRR: 96 modules" in combined_docs
