import json
from pathlib import Path

from src.paper_trading.recorded_backtest_review_workflow_close_pack import (
    build_and_write_recorded_backtest_review_workflow_close_report,
    build_recorded_backtest_review_workflow_close_report,
    safety_notice,
)


REVIEW_ITEMS = [
    "dataset_input_review",
    "run_order_review",
    "trade_ledger_review",
    "metrics_review",
    "report_review",
    "verification_review",
    "operator_review_checklist",
    "git_guard_review",
]


def _review_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "review_area": "review",
        "evidence_source": f"{name}_evidence",
        "review_instruction": f"{name} instruction",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _summary(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = REVIEW_ITEMS

    review_items = [
        _review_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_recorded_backtest_review_close": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "review_summary_item_count": len(review_items),
        "presence_check_count": 8,
        "expected_output_count": 8,
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 86,
        "phase_3_pending_after_module": 1,
        "full_hqe_product_estimate_after_module": "78-83%",
        "recommended_next_action": "close workflow",
        "safety_notice": "paper/simulation recorded backtest review summary pack only",
        "issues": [] if issues is None else issues,
        "review_items": review_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_recorded_backtest_review_workflow_close_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation recorded backtest review workflow close pack" in notice
    assert "closes the recorded-data paper backtest review workflow" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_recorded_backtest_review_summary_pack_fails(tmp_path):
    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.recorded_backtest_review_workflow_closed is False
    assert any(
        issue.code == "recorded_backtest_review_summary_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_recorded_backtest_review_summary_pack_fails(tmp_path):
    path = tmp_path / "summary.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_summary_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_review_summary_closes_workflow(tmp_path):
    path = _write_json(tmp_path / "summary.json", _summary())

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    checklist_names = {item.item_name for item in report.close_checklist}

    assert report.status == "pass"
    assert report.recorded_backtest_review_workflow_closed is True
    assert report.ready_for_next_paper_analysis_phase is True
    assert report.close_checklist_item_count == 8
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.present_required_file_count == 7
    assert report.missing_required_file_count == 0
    assert "trade_ledger_review_closed" in checklist_names
    assert "safety_boundary_closed" in checklist_names
    assert report.completed_total_before_module == 86
    assert report.completed_total_after_module == 87
    assert report.phase_3_pending_after_module == 0
    assert report.full_hqe_product_estimate_after_module == "79-84%"


def test_warning_review_summary_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "summary.json",
        _summary(status="warn", ready=True),
    )

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_summary_pack_warn"
        for issue in report.issues
    )


def test_warning_review_summary_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "summary.json",
        _summary(status="warn", ready=True),
    )

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.recorded_backtest_review_workflow_closed is True
    assert report.ready_for_next_paper_analysis_phase is True


def test_not_ready_review_summary_fails(tmp_path):
    path = _write_json(
        tmp_path / "summary.json",
        _summary(status="pass", ready=False),
    )

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_summary_pack_not_ready"
        for issue in report.issues
    )


def test_summary_fail_issues_fail_workflow_close(tmp_path):
    path = _write_json(
        tmp_path / "summary.json",
        _summary(
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

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_review_summary_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_review_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "summary.json",
        _summary(names=REVIEW_ITEMS[:3]),
    )

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_recorded_backtest_review_items_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "summary.json",
        _summary(missing_required=2),
    )

    report = build_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "recorded_backtest_review_close_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "summary.json", _summary())

    report, outputs = build_and_write_recorded_backtest_review_workflow_close_report(
        recorded_backtest_review_summary_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["recorded_backtest_review_workflow_close_pack_txt"].read_text(
        encoding="utf-8"
    )
    checklist_csv = outputs["recorded_backtest_review_workflow_close_checklist_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_BACKTEST_REVIEW_WORKFLOW_CLOSE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["recorded_backtest_review_workflow_close_pack_json"].exists()
    assert "item_index,item_name,status,evidence,next_instruction" in checklist_csv
    assert "trade_ledger_review_closed" in checklist_csv
    assert "safety_boundary_closed" in checklist_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["recorded_backtest_review_workflow_closed"] is True
    assert manifest["phase_3_pending_after_module"] == 0
    assert "hqe_recorded_backtest_review_workflow_close_pack.bat" in combined_docs
    assert "recorded backtest review workflow close pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module IIII: 87 modules" in combined_docs
