import json
from pathlib import Path

from src.paper_trading.paper_backtest_metrics_context_snapshot_pack import (
    build_and_write_paper_backtest_metrics_context_snapshot_report,
    build_paper_backtest_metrics_context_snapshot_report,
    safety_notice,
)


LEDGER_ITEMS = [
    "ledger_file_context_snapshot",
    "ledger_schema_snapshot",
    "paper_direction_mapping_snapshot",
    "neutral_no_trade_snapshot",
    "entry_exit_trace_snapshot",
    "cost_reference_snapshot",
    "ledger_missing_data_snapshot",
    "ledger_git_guard_snapshot",
]


def _ledger_item(index, name):
    return {
        "item_index": index,
        "item_name": name,
        "ledger_area": "ledger",
        "evidence_source": f"{name}_evidence",
        "snapshot_instruction": f"{name} instruction",
        "safety_boundary": "paper only; not a profitability claim",
    }


def _ledger_snapshot(
    status="pass",
    ready=True,
    names=None,
    missing_required=0,
    issues=None,
):
    if names is None:
        names = LEDGER_ITEMS

    ledger_snapshot_items = [
        _ledger_item(index, name)
        for index, name in enumerate(names, start=1)
    ]

    return {
        "status": status,
        "ready_for_metrics_context_snapshot": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "ledger_snapshot_item_count": len(ledger_snapshot_items),
        "analysis_item_count": 8,
        "review_summary_item_count": 8,
        "presence_check_count": 8,
        "expected_output_count": 8,
        "present_required_file_count": max(0, 7 - missing_required),
        "missing_required_file_count": missing_required,
        "completed_total_after_module": 89,
        "phase_4_pending_after_module": 4,
        "full_hqe_product_estimate_after_module": "81-86%",
        "recommended_next_action": "build metrics context snapshot",
        "safety_notice": "paper/simulation paper backtest ledger evidence snapshot pack only",
        "issues": [] if issues is None else issues,
        "ledger_snapshot_items": ledger_snapshot_items,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_metrics_context_snapshot_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation paper backtest metrics context snapshot pack" in notice
    assert "metrics context snapshot items" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not import or require streamlit at runtime" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_paper_backtest_ledger_evidence_snapshot_fails(tmp_path):
    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_report_safety_snapshot is False
    assert any(
        issue.code == "paper_backtest_ledger_evidence_snapshot_pack_missing"
        for issue in report.issues
    )


def test_invalid_json_paper_backtest_ledger_evidence_snapshot_fails(tmp_path):
    path = tmp_path / "ledger_snapshot.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_ledger_evidence_snapshot_pack_invalid_json"
        for issue in report.issues
    )


def test_valid_ledger_snapshot_creates_metrics_context_snapshot(tmp_path):
    path = _write_json(tmp_path / "ledger_snapshot.json", _ledger_snapshot())

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    item_names = {item.item_name for item in report.metrics_context_items}

    assert report.status == "pass"
    assert report.ready_for_report_safety_snapshot is True
    assert report.metrics_context_item_count == 9
    assert report.ledger_snapshot_item_count == 8
    assert report.analysis_item_count == 8
    assert report.review_summary_item_count == 8
    assert report.presence_check_count == 8
    assert report.expected_output_count == 8
    assert report.missing_required_file_count == 0
    assert "metrics_file_context_snapshot" in item_names
    assert "cost_slippage_context_snapshot" in item_names
    assert "metrics_git_guard_snapshot" in item_names
    assert report.completed_total_before_module == 89
    assert report.completed_total_after_module == 90
    assert report.phase_4_pending_after_module == 3
    assert report.full_hqe_product_estimate_after_module == "82-87%"


def test_warning_ledger_snapshot_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "ledger_snapshot.json",
        _ledger_snapshot(status="warn", ready=True),
    )

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_ledger_evidence_snapshot_pack_warn"
        for issue in report.issues
    )


def test_warning_ledger_snapshot_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "ledger_snapshot.json",
        _ledger_snapshot(status="warn", ready=True),
    )

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_report_safety_snapshot is True


def test_not_ready_ledger_snapshot_fails(tmp_path):
    path = _write_json(
        tmp_path / "ledger_snapshot.json",
        _ledger_snapshot(status="pass", ready=False),
    )

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_ledger_evidence_snapshot_pack_not_ready"
        for issue in report.issues
    )


def test_ledger_snapshot_fail_issues_fail_metrics_context(tmp_path):
    path = _write_json(
        tmp_path / "ledger_snapshot.json",
        _ledger_snapshot(
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

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "paper_backtest_ledger_evidence_snapshot_contains_fail_issues"
        for issue in report.issues
    )


def test_missing_required_ledger_snapshot_items_fail(tmp_path):
    path = _write_json(
        tmp_path / "ledger_snapshot.json",
        _ledger_snapshot(names=LEDGER_ITEMS[:3]),
    )

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "required_paper_backtest_ledger_snapshot_items_missing"
        for issue in report.issues
    )


def test_missing_required_files_still_fail(tmp_path):
    path = _write_json(
        tmp_path / "ledger_snapshot.json",
        _ledger_snapshot(missing_required=2),
    )

    report = build_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.missing_required_file_count == 2
    assert any(
        issue.code == "paper_backtest_metrics_context_missing_required_files"
        for issue in report.issues
    )


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "ledger_snapshot.json", _ledger_snapshot())

    report, outputs = build_and_write_paper_backtest_metrics_context_snapshot_report(
        paper_backtest_ledger_evidence_snapshot_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["paper_backtest_metrics_context_snapshot_pack_txt"].read_text(
        encoding="utf-8"
    )
    items_csv = outputs["paper_backtest_metrics_context_items_csv"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/PAPER_BACKTEST_METRICS_CONTEXT_SNAPSHOT_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["paper_backtest_metrics_context_snapshot_pack_json"].exists()
    assert "item_index,item_name,metrics_area,evidence_source,context_instruction,safety_boundary" in items_csv
    assert "metrics_file_context_snapshot" in items_csv
    assert "metrics_git_guard_snapshot" in items_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_report_safety_snapshot"] is True
    assert "hqe_paper_backtest_metrics_context_snapshot_pack.bat" in combined_docs
    assert "paper backtest metrics context snapshot pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module LLLL: 90 modules" in combined_docs
