import json
from pathlib import Path

from src.paper_trading.paper_improvement_acceptance_gate_pack import (
    build_and_write_paper_improvement_acceptance_gate_report,
    build_paper_improvement_acceptance_gate_report,
    safety_notice,
)


RERUN_GATES = [
    "git_clean_before_rerun_gate",
    "baseline_frozen_before_rerun_gate",
    "dataset_scope_before_rerun_gate",
    "ledger_quality_before_rerun_gate",
    "direction_mapping_before_rerun_gate",
    "metrics_context_before_rerun_gate",
    "cost_risk_before_rerun_gate",
    "report_language_before_rerun_gate",
    "regression_tests_before_rerun_gate",
    "paper_only_rerun_boundary_gate",
]


def _gate(index, name):
    return {
        "item_index": index,
        "gate_name": name,
        "gate_area": "rerun",
        "evidence_source": f"{name}_evidence",
        "gate_requirement": f"{name} requirement",
        "rerun_status": "not_run",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _rerun_gate(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = RERUN_GATES

    rerun_readiness_gate_items = [
        _gate(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_paper_improvement_acceptance_gate": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "rerun_readiness_gate_item_count": len(rerun_readiness_gate_items),
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
        "completed_total_after_module": 97,
        "phase_5_pending_after_module": 2,
        "full_hqe_product_estimate_after_module": "89-94%",
        "recommended_next_action": "build acceptance gate",
        "safety_notice": "paper/simulation paper improvement rerun readiness gate pack only",
        "issues": [] if issues is None else issues,
        "rerun_readiness_gate_items": rerun_readiness_gate_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_acceptance_gate_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper improvement acceptance gate pack" in notice
    assert "paper-only acceptance gate" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_rerun_readiness_gate_fails(tmp_path):
    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_paper_improvement_readiness_close is False
    assert any(
        issue.code == "paper_improvement_rerun_readiness_gate_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_rerun_readiness_gate_fails(tmp_path):
    path = tmp_path / "rerun_gate.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_rerun_readiness_gate_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_rerun_readiness_gate_creates_acceptance_gate(tmp_path):
    path = _write_json(tmp_path / "rerun_gate.json", _rerun_gate())

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    acceptance_names = {
        item.acceptance_gate_name for item in report.acceptance_gate_items
    }

    assert report.status == "pass"
    assert report.ready_for_paper_improvement_readiness_close is True
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
    assert "paper_only_acceptance_gate" in acceptance_names
    assert "no_backtest_rerun_acceptance_gate" in acceptance_names
    assert "git_output_acceptance_gate" in acceptance_names
    assert report.completed_total_before_module == 97
    assert report.completed_total_after_module == 98
    assert report.phase_5_pending_after_module == 1
    assert report.full_hqe_product_estimate_after_module == "90-95%"


def test_warning_rerun_readiness_gate_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "rerun_gate.json",
        _rerun_gate(status="warn", ready=True),
    )

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_rerun_readiness_gate_pack_warn"
        for issue in report.issues
    )


def test_warning_rerun_readiness_gate_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "rerun_gate.json",
        _rerun_gate(status="warn", ready=True),
    )

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_paper_improvement_readiness_close is True


def test_not_ready_rerun_readiness_gate_fails(tmp_path):
    path = _write_json(
        tmp_path / "rerun_gate.json",
        _rerun_gate(status="pass", ready=False),
    )

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_rerun_readiness_gate_pack_not_ready"
        for issue in report.issues
    )


def test_rerun_readiness_gate_fail_issues_fail_acceptance_gate(tmp_path):
    path = _write_json(
        tmp_path / "rerun_gate.json",
        _rerun_gate(
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

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_improvement_rerun_readiness_gate_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_rerun_readiness_gates_fail(tmp_path):
    path = _write_json(
        tmp_path / "rerun_gate.json",
        _rerun_gate(names=RERUN_GATES[:3]),
    )

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_improvement_rerun_readiness_gates_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "rerun_gate.json",
        _rerun_gate(missing_required=2),
    )

    report = build_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_improvement_acceptance_gate_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "rerun_gate.json", _rerun_gate())

    report, outputs = build_and_write_paper_improvement_acceptance_gate_report(
        paper_improvement_rerun_readiness_gate_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_improvement_acceptance_gate_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_improvement_acceptance_gate_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_IMPROVEMENT_ACCEPTANCE_GATE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_improvement_acceptance_gate_pack_json"].exists()
    assert "item_index,acceptance_gate_name,acceptance_area,evidence_source,acceptance_requirement,acceptance_status,safety_boundary" in items_csv
    assert "paper_only_acceptance_gate" in items_csv
    assert "git_output_acceptance_gate" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_paper_improvement_readiness_close"] is True
    assert "hqe_paper_improvement_acceptance_gate_pack.bat" in combined_docs
    assert "paper improvement acceptance gate pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module TTTT: 98 modules" in combined_docs
