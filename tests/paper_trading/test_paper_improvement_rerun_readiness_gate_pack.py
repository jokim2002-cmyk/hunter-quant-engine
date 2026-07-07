import json
from pathlib import Path

from src.paper_trading.paper_improvement_rerun_readiness_gate_pack import (
    build_and_write_paper_improvement_rerun_readiness_gate_report,
    build_paper_improvement_rerun_readiness_gate_report,
    safety_notice,
)


TEST_PLANS = [
    "baseline_documentation_test_plan",
    "dataset_scope_test_plan",
    "ledger_quality_test_plan",
    "direction_mapping_test_plan",
    "metrics_context_test_plan",
    "cost_risk_note_test_plan",
    "report_language_guard_test_plan",
    "regression_test_plan_test_plan",
    "paper_rerun_boundary_test_plan",
    "generated_output_git_guard_test_plan",
]


def _test_plan_item(index, name):
    return {
        "item_index": index,
        "test_plan_name": name,
        "test_area": "testing",
        "evidence_source": f"{name}_evidence",
        "test_instruction": f"{name} instruction",
        "required_before_status": "required_before_any_future_change",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _test_plan(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = TEST_PLANS

    test_plan_items = [
        _test_plan_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_paper_rerun_readiness_gate": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "test_plan_item_count": len(test_plan_items),
        "candidate_registry_item_count": 10,
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
        "completed_total_after_module": 96,
        "phase_5_pending_after_module": 3,
        "full_hqe_product_estimate_after_module": "88-93%",
        "recommended_next_action": "build rerun readiness gate",
        "safety_notice": "paper/simulation paper improvement candidate test plan pack only",
        "issues": [] if issues is None else issues,
        "test_plan_items": test_plan_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_rerun_readiness_gate_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper improvement rerun readiness gate pack" in notice
    assert "paper-only rerun readiness gates" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_candidate_test_plan_fails(tmp_path):
    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_paper_improvement_acceptance_gate is False
    assert any(
        issue.code == "paper_improvement_candidate_test_plan_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_candidate_test_plan_fails(tmp_path):
    path = tmp_path / "test_plan.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_test_plan_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_candidate_test_plan_creates_rerun_gate(tmp_path):
    path = _write_json(tmp_path / "test_plan.json", _test_plan())

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    gate_names = {item.gate_name for item in report.rerun_readiness_gate_items}

    assert report.status == "pass"
    assert report.ready_for_paper_improvement_acceptance_gate is True
    assert report.rerun_readiness_gate_item_count == 10
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
    assert "git_clean_before_rerun_gate" in gate_names
    assert "paper_only_rerun_boundary_gate" in gate_names
    assert "report_language_before_rerun_gate" in gate_names
    assert report.completed_total_before_module == 96
    assert report.completed_total_after_module == 97
    assert report.phase_5_pending_after_module == 2
    assert report.full_hqe_product_estimate_after_module == "89-94%"


def test_warning_candidate_test_plan_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "test_plan.json",
        _test_plan(status="warn", ready=True),
    )

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_test_plan_pack_warn"
        for issue in report.issues
    )


def test_warning_candidate_test_plan_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "test_plan.json",
        _test_plan(status="warn", ready=True),
    )

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_paper_improvement_acceptance_gate is True


def test_not_ready_candidate_test_plan_fails(tmp_path):
    path = _write_json(
        tmp_path / "test_plan.json",
        _test_plan(status="pass", ready=False),
    )

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_test_plan_pack_not_ready"
        for issue in report.issues
    )


def test_candidate_test_plan_fail_issues_fail_rerun_gate(tmp_path):
    path = _write_json(
        tmp_path / "test_plan.json",
        _test_plan(
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

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_candidate_test_plan_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_test_plans_fail(tmp_path):
    path = _write_json(
        tmp_path / "test_plan.json",
        _test_plan(names=TEST_PLANS[:3]),
    )

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_improvement_test_plans_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "test_plan.json",
        _test_plan(missing_required=2),
    )

    report = build_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_improvement_rerun_readiness_gate_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "test_plan.json", _test_plan())

    report, outputs = build_and_write_paper_improvement_rerun_readiness_gate_report(
        paper_improvement_candidate_test_plan_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_improvement_rerun_readiness_gate_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_improvement_rerun_readiness_gate_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_IMPROVEMENT_RERUN_READINESS_GATE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_improvement_rerun_readiness_gate_pack_json"].exists()
    assert "item_index,gate_name,gate_area,evidence_source,gate_requirement,rerun_status,safety_boundary" in items_csv
    assert "git_clean_before_rerun_gate" in items_csv
    assert "paper_only_rerun_boundary_gate" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_paper_improvement_acceptance_gate"] is True
    assert "hqe_paper_improvement_rerun_readiness_gate_pack.bat" in combined_docs
    assert "paper improvement rerun readiness gate pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module SSSS: 97 modules" in combined_docs
