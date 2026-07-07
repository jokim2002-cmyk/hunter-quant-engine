import json
from pathlib import Path

from src.paper_trading.paper_improvement_readiness_launch_pack import (
    build_and_write_paper_improvement_readiness_launch_report,
    build_paper_improvement_readiness_launch_report,
    safety_notice,
)


CLOSE_ITEMS = [
    "paper_only_scope_closed",
    "dataset_context_closed",
    "descriptive_metrics_closed",
    "direction_mapping_closed",
    "neutral_filter_closed",
    "cost_assumption_closed",
    "risk_language_closed",
    "limitation_language_closed",
    "no_winner_closed",
    "git_generated_output_closed",
    "phase_4_closed",
]


def _close_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "status": "closed",
        "evidence": f"{name} evidence",
        "next_instruction": f"{name} next",
    }


def _phase_4_close(
    status="pass",
    closed=True,
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = CLOSE_ITEMS

    close_checklist = [
        _close_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "paper_backtest_evidence_analysis_sprint_closed": closed,
        "ready_for_next_paper_improvement_phase": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "close_checklist_item_count": len(close_checklist),
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
        "completed_total_after_module": 93,
        "phase_4_pending_after_module": 0,
        "full_hqe_product_estimate_after_module": "85-90%",
        "recommended_next_phase": "paper improvement readiness phase",
        "safety_notice": "paper/simulation paper backtest evidence analysis sprint close pack only",
        "issues": [] if issues is None else issues,
        "close_checklist": close_checklist,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_paper_improvement_readiness_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper improvement readiness launch pack" in notice
    assert "paper-only improvement readiness sprint" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_phase_4_close_pack_fails(tmp_path):
    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_paper_improvement_readiness is False
    assert any(
        issue.code == "paper_backtest_evidence_analysis_sprint_close_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_phase_4_close_pack_fails(tmp_path):
    path = tmp_path / "phase4_close.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_sprint_close_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_phase_4_close_creates_improvement_readiness_launch(tmp_path):
    path = _write_json(tmp_path / "phase4_close.json", _phase_4_close())

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    item_names = {item.item_name for item in report.improvement_readiness_items}

    assert report.status == "pass"
    assert report.ready_for_paper_improvement_readiness is True
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
    assert "evidence_baseline_freeze" in item_names
    assert "candidate_improvement_log" in item_names
    assert "git_output_guard" in item_names
    assert report.completed_total_before_module == 93
    assert report.completed_total_after_module == 94
    assert report.phase_5_pending_after_module == 5
    assert report.full_hqe_product_estimate_after_module == "86-91%"


def test_warning_phase_4_close_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "phase4_close.json",
        _phase_4_close(status="warn", closed=True, ready=True),
    )

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_sprint_close_pack_warn"
        for issue in report.issues
    )


def test_warning_phase_4_close_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "phase4_close.json",
        _phase_4_close(status="warn", closed=True, ready=True),
    )

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_paper_improvement_readiness is True


def test_not_closed_phase_4_fails(tmp_path):
    path = _write_json(
        tmp_path / "phase4_close.json",
        _phase_4_close(status="pass", closed=False, ready=True),
    )

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_sprint_not_closed"
        for issue in report.issues
    )


def test_not_ready_for_improvement_fails(tmp_path):
    path = _write_json(
        tmp_path / "phase4_close.json",
        _phase_4_close(status="pass", closed=True, ready=False),
    )

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_sprint_not_ready_for_improvement"
        for issue in report.issues
    )


def test_phase_4_close_fail_issues_fail_improvement_readiness_launch(tmp_path):
    path = _write_json(
        tmp_path / "phase4_close.json",
        _phase_4_close(
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

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_sprint_close_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_phase_4_close_checklist_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "phase4_close.json",
        _phase_4_close(names=CLOSE_ITEMS[:3]),
    )

    report = build_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_phase_4_close_checklist_items_missing"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "phase4_close.json", _phase_4_close())

    report, outputs = build_and_write_paper_improvement_readiness_launch_report(
        paper_backtest_evidence_analysis_sprint_close_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_improvement_readiness_launch_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_improvement_readiness_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_IMPROVEMENT_READINESS_LAUNCH_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_improvement_readiness_launch_pack_json"].exists()
    assert "item_index,item_name,readiness_area,evidence_source,readiness_instruction,safety_boundary" in items_csv
    assert "evidence_baseline_freeze" in items_csv
    assert "git_output_guard" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_paper_improvement_readiness"] is True
    assert "hqe_paper_improvement_readiness_launch_pack.bat" in combined_docs
    assert "paper improvement readiness launch pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module PPPP: 94 modules" in combined_docs
