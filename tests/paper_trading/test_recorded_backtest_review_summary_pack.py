import json
from pathlib import Path

from src.paper_trading.recorded_backtest_review_summary_pack import (
    build_and_write_recorded_backtest_review_summary_report,
    build_recorded_backtest_review_summary_report,
    safety_notice,
)


PRESENCE_OUTPUTS = [
    "real_dataset_backtest_input_pack",
    "first_real_dataset_backtest_run_pack",
    "backtest_trade_ledger",
    "backtest_metrics",
    "backtest_report",
    "first_real_backtest_output_verification",
    "first_real_backtest_report_review",
    "git_generated_outputs_guard",
]


def _presence_check(index, name, exists=True):
    return {
        "check_index": index,
        "output_name": name,
        "expected_path_hint": f"reports/paper_trading/{name}/{name}.json",
        "resolved_path": f"reports/paper_trading/{name}/{name}.json",
        "required_after_manual_run": True,
        "exists": exists,
        "check_status": "present" if exists else "missing",
        "intake_check": f"{name} intake",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _presence_pack(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = PRESENCE_OUTPUTS

    checks = [
        _presence_check(index, name, exists=True)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_recorded_backtest_review_summary": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "expected_output_count": len(names),
        "presence_check_count": len(checks),
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 85,
        "phase_3_pending_after_module": 2,
        "full_hqe_product_estimate_after_module": "77-82%",
        "recommended_next_action": "build review summary",
        "safety_notice": "paper/simulation recorded backtest output presence verification pack only",
        "issues": [] if issues is None else issues,
        "presence_checks": checks,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_recorded_backtest_review_summary_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation recorded backtest review summary pack" in notice
    assert "verified recorded-data paper backtest output presence evidence" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_recorded_backtest_output_presence_pack_fails(tmp_path):
    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_recorded_backtest_review_close is False
    assert any(
        issue.code == "recorded_backtest_output_presence_verification_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_recorded_backtest_output_presence_pack_fails(tmp_path):
    path = tmp_path / "presence.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_output_presence_verification_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_presence_pack_creates_review_summary(tmp_path):
    path = _write_json(tmp_path / "presence.json", _presence_pack())

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    item_names = {item.item_name for item in report.review_items}

    assert report.status == "pass"
    assert report.ready_for_recorded_backtest_review_close is True
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.present_required_file_count == 7
    assert report.missing_required_file_count == 0
    assert "trade_ledger_review" in item_names
    assert "metrics_review" in item_names
    assert "git_guard_review" in item_names
    assert report.completed_total_before_module == 85
    assert report.completed_total_after_module == 86
    assert report.phase_3_pending_after_module == 1
    assert report.full_hqe_product_estimate_after_module == "78-83%"


def test_warning_presence_pack_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "presence.json",
        _presence_pack(status="warn", ready=True),
    )

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_output_presence_verification_pack_warn"
        for issue in report.issues
    )


def test_warning_presence_pack_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "presence.json",
        _presence_pack(status="warn", ready=True),
    )

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_recorded_backtest_review_close is True


def test_not_ready_presence_pack_fails(tmp_path):
    path = _write_json(
        tmp_path / "presence.json",
        _presence_pack(status="pass", ready=False),
    )

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_output_presence_verification_pack_not_ready"
        for issue in report.issues
    )


def test_presence_pack_fail_issues_fail_review_summary(tmp_path):
    path = _write_json(
        tmp_path / "presence.json",
        _presence_pack(
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

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "recorded_backtest_output_presence_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_presence_outputs_fail(tmp_path):
    path = _write_json(
        tmp_path / "presence.json",
        _presence_pack(names=PRESENCE_OUTPUTS[:3]),
    )

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_recorded_backtest_presence_outputs_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "presence.json",
        _presence_pack(missing_required=2),
    )

    report = build_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "recorded_backtest_required_files_still_missing"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "presence.json", _presence_pack())

    report, outputs = build_and_write_recorded_backtest_review_summary_report(
        recorded_backtest_output_presence_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["recorded_backtest_review_summary_pack_txt"].read_text(encoding="utf-8")
    summary_csv = outputs["recorded_backtest_review_summary_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/RECORDED_BACKTEST_REVIEW_SUMMARY_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["recorded_backtest_review_summary_pack_json"].exists()
    assert "item_index,item_name,review_area,evidence_source,review_instruction,safety_boundary" in summary_csv
    assert "trade_ledger_review" in summary_csv
    assert "git_guard_review" in summary_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_recorded_backtest_review_close"] is True
    assert "hqe_recorded_backtest_review_summary_pack.bat" in combined_docs
    assert "recorded backtest review summary pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module HHHH: 86 modules" in combined_docs
