import json
from pathlib import Path

from src.paper_trading.dashboard_input_index_pack import (
    build_and_write_dashboard_input_index_report,
    build_dashboard_input_index_report,
    safety_notice,
)


def _close_pack(status="pass", phase_closed=True, ready=True, issues=None):
    return {
        "status": status,
        "phase_1_closed": phase_closed,
        "ready_for_future_dashboard_sprint": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "completed_total_after_module": 73,
        "phase_1_pending_after_module": 0,
        "full_hqe_product_estimate_after_module": "65-70%",
        "safety_notice": "paper/simulation real backtest usage sprint readiness close only",
        "issues": [] if issues is None else issues,
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_dashboard_input_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation dashboard input index pack" in notice
    assert "does not start a dashboard ui" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_readiness_close_fails(tmp_path):
    report = build_dashboard_input_index_report(
        readiness_close_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_streamlit_dashboard is False
    assert any(issue.code == "real_backtest_usage_sprint_readiness_close_missing" for issue in report.issues)


def test_invalid_json_readiness_close_fails(tmp_path):
    path = tmp_path / "close.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "real_backtest_usage_sprint_readiness_close_invalid_json" for issue in report.issues)


def test_valid_readiness_close_creates_dashboard_input_index(tmp_path):
    path = _write_json(tmp_path / "close.json", _close_pack())

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_streamlit_dashboard is True
    assert report.entry_count == 10
    assert report.existing_entry_count >= 1
    assert report.completed_total_before_module == 73
    assert report.completed_total_after_module == 74
    assert report.phase_2_pending_after_module == 7
    assert report.full_hqe_product_estimate_after_module == "66-71%"


def test_warning_readiness_close_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="warn", phase_closed=True, ready=True),
    )

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "real_backtest_usage_sprint_readiness_close_warn" for issue in report.issues)


def test_warning_readiness_close_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="warn", phase_closed=True, ready=True),
    )

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_streamlit_dashboard is True


def test_not_closed_phase_1_fails(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="pass", phase_closed=False, ready=True),
    )

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "real_backtest_usage_sprint_not_closed" for issue in report.issues)


def test_not_ready_for_dashboard_fails(tmp_path):
    path = _write_json(
        tmp_path / "close.json",
        _close_pack(status="pass", phase_closed=True, ready=False),
    )

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "not_ready_for_future_dashboard_sprint" for issue in report.issues)


def test_readiness_close_fail_issues_fail_index(tmp_path):
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

    report = build_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "readiness_close_contains_fail_issues" for issue in report.issues)


def test_build_and_write_outputs_include_entries_csv(tmp_path):
    path = _write_json(tmp_path / "close.json", _close_pack())

    report, outputs = build_and_write_dashboard_input_index_report(
        readiness_close_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["dashboard_input_index_pack_txt"].read_text(encoding="utf-8")
    entries_csv = outputs["dashboard_input_entries_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["dashboard_input_index_pack_json"].exists()
    assert "entry_index,entry_name,category,required_for_dashboard,exists,path,description" in entries_csv
    assert "strategy_mode_cost_adjusted_comparison_pack" in entries_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_streamlit_dashboard"] is True


def test_docs_reference_dashboard_input_index_pack():
    doc_paths = [
        Path("docs/DASHBOARD_INPUT_INDEX_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_dashboard_input_index_pack.bat" in combined_docs
    assert "dashboard input index pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
    assert "Completed total after Module VVV: 74 modules" in combined_docs
