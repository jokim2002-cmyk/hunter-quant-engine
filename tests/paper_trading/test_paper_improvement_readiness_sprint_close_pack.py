import json
from pathlib import Path

from src.paper_trading.paper_improvement_readiness_sprint_close_pack import (
    build_and_write_paper_improvement_readiness_sprint_close_report,
    build_paper_improvement_readiness_sprint_close_report,
    safety_notice,
)


ACCEPTANCE_GATES = [
    "paper_only_acceptance_gate",
    "no_backtest_rerun_acceptance_gate",
    "no_strategy_change_acceptance_gate",
    "dataset_scope_acceptance_gate",
    "ledger_quality_acceptance_gate",
    "direction_mapping_acceptance_gate",
    "metrics_language_acceptance_gate",
    "cost_risk_acceptance_gate",
    "report_safety_acceptance_gate",
    "test_guard_acceptance_gate",
    "git_output_acceptance_gate",
]


def _acceptance_item(index, name):
    return {
        "item_index": index,
        "acceptance_gate_name": name,
        "acceptance_area": "acceptance",
        "evidence_source": f"{name}_evidence",
        "acceptance_requirement": f"{name} requirement",
        "acceptance_status": "accepted_when_source_gate_passes",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _acceptance_gate(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = ACCEPTANCE_GATES

    acceptance_gate_items = [
        _acceptance_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_paper_improvement_readiness_close": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "acceptance_gate_item_count": len(acceptance_gate_items),
        "rerun_readiness_gate_item_count": 10,
        "test_plan_item_count": 10,
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
        "completed_total_after_module": 98,
        "phase_5_pending_after_module": 1,
        "full_hqe_product_estimate_after_module": "90-95%",
        "recommended_next_action": "close phase 5",
        "safety_notice": "paper/simulation paper improvement acceptance gate pack only",
        "issues": [] if issues is None else issues,
        "acceptance_gate_items": acceptance_gate_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_readiness_sprint_close_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper improvement readiness sprint close pack" in notice
    assert "closes the paper improvement readiness sprint" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_acceptance_gate_fails(tmp_path):
    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.paper_improvement_readiness_sprint_closed is False
    assert any(
        issue.code == "paper_improvement_acceptance_gate_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_acceptance_gate_fails(tmp_path):
    path = tmp_path / "acceptance_gate.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_acceptance_gate_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_acceptance_gate_closes_phase_5(tmp_path):
    path = _write_json(tmp_path / "acceptance_gate.json", _acceptance_gate())

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    checklist_names = {item.item_name for item in report.close_checklist}

    assert report.status == "pass"
    assert report.paper_improvement_readiness_sprint_closed is True
    assert report.ready_for_next_paper_planning_phase is True
    assert report.close_checklist_item_count == 12
    assert report.acceptance_gate_item_count == 11
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
    assert "paper_only_acceptance_closed" in checklist_names
    assert "phase_5_closed" in checklist_names
    assert "no_strategy_change_closed" in checklist_names
    assert report.completed_total_before_module == 98
    assert report.completed_total_after_module == 99
    assert report.phase_5_pending_after_module == 0
    assert report.full_hqe_product_estimate_after_module == "91-96%"


def test_warning_acceptance_gate_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "acceptance_gate.json",
        _acceptance_gate(status="warn", ready=True),
    )

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_acceptance_gate_pack_warn"
        for issue in report.issues
    )


def test_warning_acceptance_gate_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "acceptance_gate.json",
        _acceptance_gate(status="warn", ready=True),
    )

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.paper_improvement_readiness_sprint_closed is True
    assert report.ready_for_next_paper_planning_phase is True


def test_not_ready_acceptance_gate_fails(tmp_path):
    path = _write_json(
        tmp_path / "acceptance_gate.json",
        _acceptance_gate(status="pass", ready=False),
    )

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_acceptance_gate_pack_not_ready"
        for issue in report.issues
    )


def test_acceptance_gate_fail_issues_fail_sprint_close(tmp_path):
    path = _write_json(
        tmp_path / "acceptance_gate.json",
        _acceptance_gate(
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

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_acceptance_gate_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_acceptance_gates_fail(tmp_path):
    path = _write_json(
        tmp_path / "acceptance_gate.json",
        _acceptance_gate(names=ACCEPTANCE_GATES[:3]),
    )

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_improvement_acceptance_gates_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "acceptance_gate.json",
        _acceptance_gate(missing_required=2),
    )

    report = build_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_improvement_readiness_sprint_close_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "acceptance_gate.json", _acceptance_gate())

    report, outputs = build_and_write_paper_improvement_readiness_sprint_close_report(
        paper_improvement_acceptance_gate_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_improvement_readiness_sprint_close_pack_txt"].read_text(
        encoding="utf-8"
    )
    checklist_csv = outputs["paper_improvement_readiness_sprint_close_checklist_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_IMPROVEMENT_READINESS_SPRINT_CLOSE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_improvement_readiness_sprint_close_pack_json"].exists()
    assert "item_index,item_name,status,evidence,next_instruction" in checklist_csv
    assert "phase_5_closed" in checklist_csv
    assert "no_strategy_change_closed" in checklist_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["paper_improvement_readiness_sprint_closed"] is True
    assert manifest["phase_5_pending_after_module"] == 0
    assert "hqe_paper_improvement_readiness_sprint_close_pack.bat" in combined_docs
    assert "paper improvement readiness sprint close pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module UUUU: 99 modules" in combined_docs
