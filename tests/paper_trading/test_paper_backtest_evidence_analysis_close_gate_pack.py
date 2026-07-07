import json
from pathlib import Path

from src.paper_trading.paper_backtest_evidence_analysis_close_gate_pack import (
    build_and_write_paper_backtest_evidence_analysis_close_gate_report,
    build_paper_backtest_evidence_analysis_close_gate_report,
    safety_notice,
)


LANGUAGE_ITEMS = [
    "paper_only_header_language",
    "dataset_context_language",
    "descriptive_metrics_language",
    "direction_mapping_language",
    "neutral_filter_language",
    "cost_assumption_language",
    "risk_language",
    "limitation_language",
    "no_winner_language",
    "git_generated_output_language",
]


def _language_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "language_area": "safety",
        "evidence_source": f"{name}_evidence",
        "wording_instruction": f"{name} instruction",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _language_snapshot(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = LANGUAGE_ITEMS

    report_safety_language_items = [
        _language_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_evidence_analysis_close": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "report_safety_language_item_count": len(report_safety_language_items),
        "metrics_context_item_count": 9,
        "ledger_snapshot_item_count": 8,
        "analysis_item_count": 8,
        "review_summary_item_count": 8,
        "presence_check_count": 8,
        "expected_output_count": 8,
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 91,
        "phase_4_pending_after_module": 2,
        "full_hqe_product_estimate_after_module": "83-88%",
        "recommended_next_action": "build close gate",
        "safety_notice": "paper/simulation paper backtest report safety language snapshot pack only",
        "issues": [] if issues is None else issues,
        "report_safety_language_items": report_safety_language_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_evidence_analysis_close_gate_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper backtest evidence analysis close gate pack" in notice
    assert "final paper-only close gate" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_report_safety_language_snapshot_fails(tmp_path):
    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_phase_4_close is False
    assert any(
        issue.code == "paper_backtest_report_safety_language_snapshot_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_report_safety_language_snapshot_fails(tmp_path):
    path = tmp_path / "language_snapshot.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_report_safety_language_snapshot_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_report_safety_language_snapshot_creates_close_gate(tmp_path):
    path = _write_json(tmp_path / "language_snapshot.json", _language_snapshot())

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    gate_names = {item.gate_name for item in report.close_gate_items}

    assert report.status == "pass"
    assert report.ready_for_phase_4_close is True
    assert report.close_gate_item_count == 10
    assert report.report_safety_language_item_count == 10
    assert report.metrics_context_item_count == 9
    assert report.ledger_snapshot_item_count == 8
    assert report.analysis_item_count == 8
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.missing_required_file_count == 0
    assert "paper_only_scope_gate" in gate_names
    assert "no_winner_gate" in gate_names
    assert "git_generated_output_gate" in gate_names
    assert report.completed_total_before_module == 91
    assert report.completed_total_after_module == 92
    assert report.phase_4_pending_after_module == 1
    assert report.full_hqe_product_estimate_after_module == "84-89%"


def test_warning_report_safety_language_snapshot_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "language_snapshot.json",
        _language_snapshot(status="warn", ready=True),
    )

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_report_safety_language_snapshot_pack_warn"
        for issue in report.issues
    )


def test_warning_report_safety_language_snapshot_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "language_snapshot.json",
        _language_snapshot(status="warn", ready=True),
    )

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_phase_4_close is True


def test_not_ready_report_safety_language_snapshot_fails(tmp_path):
    path = _write_json(
        tmp_path / "language_snapshot.json",
        _language_snapshot(status="pass", ready=False),
    )

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_report_safety_language_snapshot_pack_not_ready"
        for issue in report.issues
    )


def test_report_safety_language_snapshot_fail_issues_fail_close_gate(tmp_path):
    path = _write_json(
        tmp_path / "language_snapshot.json",
        _language_snapshot(
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

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_report_safety_language_snapshot_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_report_safety_language_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "language_snapshot.json",
        _language_snapshot(names=LANGUAGE_ITEMS[:3]),
    )

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_backtest_report_safety_language_items_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "language_snapshot.json",
        _language_snapshot(missing_required=2),
    )

    report = build_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_backtest_evidence_analysis_close_gate_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "language_snapshot.json", _language_snapshot())

    report, outputs = build_and_write_paper_backtest_evidence_analysis_close_gate_report(
        paper_backtest_report_safety_language_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_backtest_evidence_analysis_close_gate_pack_txt"].read_text(
        encoding="utf-8"
    )
    gate_csv = outputs["paper_backtest_evidence_analysis_close_gate_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_BACKTEST_EVIDENCE_ANALYSIS_CLOSE_GATE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_backtest_evidence_analysis_close_gate_pack_json"].exists()
    assert "item_index,gate_name,gate_area,evidence_source,gate_requirement,safety_boundary" in gate_csv
    assert "paper_only_scope_gate" in gate_csv
    assert "no_winner_gate" in gate_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_phase_4_close"] is True
    assert "hqe_paper_backtest_evidence_analysis_close_gate_pack.bat" in combined_docs
    assert "paper backtest evidence analysis close gate pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module NNNN: 92 modules" in combined_docs
