import json
from pathlib import Path

from src.paper_trading.paper_backtest_ledger_evidence_snapshot_pack import (
    build_and_write_paper_backtest_ledger_evidence_snapshot_report,
    build_paper_backtest_ledger_evidence_snapshot_report,
    safety_notice,
)


ANALYSIS_ITEMS = [
    "dataset_context_analysis",
    "ledger_integrity_analysis",
    "decision_mapping_review",
    "metrics_context_review",
    "cost_assumption_review",
    "report_safety_language_review",
    "verification_chain_review",
    "git_generated_output_guard_review",
]


def _analysis_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "analysis_area": "ledger",
        "evidence_source": f"{name}_evidence",
        "analysis_instruction": f"{name} instruction",
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
        names = ANALYSIS_ITEMS

    analysis_items = [
        _analysis_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_paper_evidence_analysis": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "analysis_item_count": len(analysis_items),
        "close_checklist_item_count": 8,
        "review_summary_item_count": 8,
        "presence_check_count": 8,
        "expected_output_count": 8,
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 88,
        "phase_4_pending_after_module": 5,
        "full_hqe_product_estimate_after_module": "80-85%",
        "recommended_next_action": "build ledger snapshot",
        "safety_notice": "paper/simulation paper backtest evidence analysis launch pack only",
        "issues": [] if issues is None else issues,
        "analysis_items": analysis_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_ledger_evidence_snapshot_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper backtest ledger evidence snapshot pack" in notice
    assert "ledger evidence snapshot items" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_paper_backtest_evidence_analysis_launch_fails(tmp_path):
    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_metrics_context_snapshot is False
    assert any(
        issue.code == "paper_backtest_evidence_analysis_launch_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_paper_backtest_evidence_analysis_launch_fails(tmp_path):
    path = tmp_path / "launch.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_launch_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_launch_creates_ledger_snapshot(tmp_path):
    path = _write_json(tmp_path / "launch.json", _launch())

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    item_names = {item.item_name for item in report.ledger_snapshot_items}

    assert report.status == "pass"
    assert report.ready_for_metrics_context_snapshot is True
    assert report.ledger_snapshot_item_count == 8
    assert report.analysis_item_count == 8
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.missing_required_file_count == 0
    assert "ledger_schema_snapshot" in item_names
    assert "paper_direction_mapping_snapshot" in item_names
    assert "ledger_git_guard_snapshot" in item_names
    assert report.completed_total_before_module == 88
    assert report.completed_total_after_module == 89
    assert report.phase_4_pending_after_module == 4
    assert report.full_hqe_product_estimate_after_module == "81-86%"


def test_warning_launch_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(status="warn", ready=True),
    )

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_launch_pack_warn"
        for issue in report.issues
    )


def test_warning_launch_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(status="warn", ready=True),
    )

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_metrics_context_snapshot is True


def test_not_ready_launch_fails(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(status="pass", ready=False),
    )

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_launch_pack_not_ready"
        for issue in report.issues
    )


def test_launch_fail_issues_fail_ledger_snapshot(tmp_path):
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

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_evidence_analysis_launch_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_analysis_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(names=ANALYSIS_ITEMS[:3]),
    )

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_backtest_analysis_items_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "launch.json",
        _launch(missing_required=2),
    )

    report = build_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_backtest_ledger_snapshot_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "launch.json", _launch())

    report, outputs = build_and_write_paper_backtest_ledger_evidence_snapshot_report(
        paper_backtest_evidence_analysis_launch_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_backtest_ledger_evidence_snapshot_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_backtest_ledger_snapshot_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_BACKTEST_LEDGER_EVIDENCE_SNAPSHOT_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_backtest_ledger_evidence_snapshot_pack_json"].exists()
    assert "item_index,item_name,ledger_area,evidence_source,snapshot_instruction,safety_boundary" in items_csv
    assert "ledger_schema_snapshot" in items_csv
    assert "ledger_git_guard_snapshot" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_metrics_context_snapshot"] is True
    assert "hqe_paper_backtest_ledger_evidence_snapshot_pack.bat" in combined_docs
    assert "paper backtest ledger evidence snapshot pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module KKKK: 89 modules" in combined_docs
