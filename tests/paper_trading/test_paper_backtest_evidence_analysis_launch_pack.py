import json
from pathlib import Path

from src.paper_trading.paper_backtest_evidence_analysis_launch_pack import (
    build_and_write_paper_backtest_evidence_analysis_launch_report,
    build_paper_backtest_evidence_analysis_launch_report,
    safety_notice,
)


CLOSE_ITEMS = [
    "dataset_input_review_closed",
    "run_order_review_closed",
    "trade_ledger_review_closed",
    "metrics_review_closed",
    "report_review_closed",
    "verification_review_closed",
    "git_guard_review_closed",
    "safety_boundary_closed",
]


def _close_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "status": "closed",
        "evidence": f"{name} evidence",
        "next_instruction": f"{name} next",
    }


def _close_pack(
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
        "recorded_backtest_review_workflow_closed": closed,
        "ready_for_next_paper_analysis_phase": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "close_checklist_item_count": len(close_checklist),
        "review_summary_item_count": 8,
        "presence_check_count": 8,
        "expected_output_count": 8,
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 87,
        "phase_3_pending_after_module": 0,
        "full_hqe_product_estimate_after_module": "79-84%",
        "recommended_next_phase": "paper-only analysis phase",
        "safety_notice": "paper/simulation recorded backtest review workflow close pack only",
        "issues": [] if issues is None else issues,
        "close_checklist": close_checklist,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_paper_backtest_evidence_analysis_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper backtest evidence analysis launch pack" in notice
    assert "paper-only evidence analysis sprint" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_recorded_backtest_review_workflow_close_fails(tmp_path):
    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_paper_evidence_analysis is False
    assert any(
        issue.code == "recorded_backtest_review_workflow_close_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_recorded_backtest_review_workflow_close_fails(tmp_path):
    path = tmp_path / "close.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_workflow_close_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_workflow_close_creates_analysis_launch(tmp_path):
    path = _write_json(tmp_path / "close.json", _close_pack())

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    item_names = {item.item_name for item in report.analysis_items}

    assert report.status == "pass"
    assert report.ready_for_paper_evidence_analysis is True
    assert report.analysis_item_count == 8
    assert report.close_checklist_item_count == 8
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.missing_required_file_count == 0
    assert "ledger_integrity_analysis" in item_names
    assert "metrics_context_review" in item_names
    assert "git_generated_output_guard_review" in item_names
    assert report.completed_total_before_module == 87
    assert report.completed_total_after_module == 88
    assert report.phase_4_pending_after_module == 5
    assert report.full_hqe_product_estimate_after_module == "80-85%"


def test_warning_workflow_close_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="warn", closed=True, ready=True),
    )

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_workflow_close_pack_warn"
        for issue in report.issues
    )


def test_warning_workflow_close_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="warn", closed=True, ready=True),
    )

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_paper_evidence_analysis is True


def test_not_closed_workflow_fails(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="pass", closed=False, ready=True),
    )

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_workflow_not_closed"
        for issue in report.issues
    )


def test_not_ready_for_analysis_fails(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="pass", closed=True, ready=False),
    )

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_workflow_not_ready_for_analysis"
        for issue in report.issues
    )


def test_workflow_close_fail_issues_fail_analysis_launch(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(
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

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_workflow_close_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_close_checklist_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(names=CLOSE_ITEMS[:3]),
    )

    report = build_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_recorded_backtest_close_checklist_items_missing"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "close.json", _close_pack())

    report, outputs = build_and_write_paper_backtest_evidence_analysis_launch_report(
        recorded_backtest_review_workflow_close_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_backtest_evidence_analysis_launch_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_backtest_evidence_analysis_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_BACKTEST_EVIDENCE_ANALYSIS_LAUNCH_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_backtest_evidence_analysis_launch_pack_json"].exists()
    assert "item_index,item_name,analysis_area,evidence_source,analysis_instruction,safety_boundary" in items_csv
    assert "ledger_integrity_analysis" in items_csv
    assert "git_generated_output_guard_review" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_paper_evidence_analysis"] is True
    assert "hqe_paper_backtest_evidence_analysis_launch_pack.bat" in combined_docs
    assert "paper backtest evidence analysis launch pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module JJJJ: 88 modules" in combined_docs
