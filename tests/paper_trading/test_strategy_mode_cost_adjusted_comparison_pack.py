import json
from pathlib import Path

from src.paper_trading.strategy_mode_cost_adjusted_comparison_pack import (
    build_and_write_cost_adjusted_mode_comparison_report,
    build_cost_adjusted_mode_comparison_report,
    safety_notice,
)


MODES = ["strict", "balanced", "relaxed"]
CATEGORIES = ["ledger", "metrics", "report", "readiness"]


def _summary(mode_name):
    return {
        "mode_name": mode_name,
        "expected_output_count": 4,
        "existing_output_count": 4,
        "missing_output_count": 0,
    }


def _result_path(mode_name, category):
    return {
        "mode_name": mode_name,
        "category": category,
        "path": f"reports/paper_trading/mode_backtests/{mode_name}/{category}.json",
        "exists": True,
        "required": True,
    }


def _comparison(status="pass", ready=True, modes=None, categories=None, issues=None):
    if modes is None:
        modes = MODES
    if categories is None:
        categories = CATEGORIES

    result_paths = []
    for mode in modes:
        for category in categories:
            result_paths.append(_result_path(mode, category))

    return {
        "status": status,
        "ready_for_future_cost_adjusted_mode_comparison": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "mode_count": len(modes),
        "expected_result_path_count": len(result_paths),
        "existing_result_path_count": len(result_paths),
        "missing_result_path_count": 0,
        "safety_notice": "paper/simulation strategy mode backtest result comparison pack only",
        "issues": [] if issues is None else issues,
        "result_paths": result_paths,
        "mode_summaries": [_summary(mode) for mode in modes],
        "mode_names": modes,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_cost_adjusted_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation cost-adjusted mode comparison pack" in notice
    assert "strict, balanced, and relaxed" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_result_comparison_pack_fails(tmp_path):
    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_strategy_selection_review is False
    assert any(issue.code == "strategy_mode_result_comparison_pack_missing" for issue in report.issues)


def test_invalid_json_result_comparison_pack_fails(tmp_path):
    path = tmp_path / "comparison.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_result_comparison_pack_invalid_json" for issue in report.issues)


def test_valid_result_comparison_creates_cost_adjusted_scaffold(tmp_path):
    path = _write_json(tmp_path / "comparison.json", _comparison())

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_strategy_selection_review is True
    assert report.mode_count == 3
    assert report.cost_assumption_count == 4
    assert report.review_item_count == 3
    assert {item.mode_name for item in report.review_items} == {"strict", "balanced", "relaxed"}


def test_warning_result_comparison_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(status="warn", ready=True),
    )

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_result_comparison_pack_warn" for issue in report.issues)


def test_warning_result_comparison_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(status="warn", ready=True),
    )

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_strategy_selection_review is True


def test_not_ready_result_comparison_fails(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(status="pass", ready=False),
    )

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_result_comparison_pack_not_ready" for issue in report.issues)


def test_result_comparison_fail_issues_fail_report(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(
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

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_mode_result_comparison_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_modes_fail(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(modes=["strict", "balanced"]),
    )

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_cost_adjusted_modes_missing" for issue in report.issues)


def test_missing_required_result_categories_fail(tmp_path):
    path = _write_json(
        tmp_path / "comparison.json",
        _comparison(categories=["ledger", "metrics"]),
    )

    report = build_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_cost_adjusted_result_categories_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_pack(tmp_path):
    path = _write_json(tmp_path / "comparison.json", _comparison())

    report, outputs = build_and_write_cost_adjusted_mode_comparison_report(
        result_comparison_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["strategy_mode_cost_adjusted_comparison_pack_txt"].read_text(encoding="utf-8")
    assumptions_csv = outputs["cost_adjustment_assumptions_csv"].read_text(encoding="utf-8")
    review_csv = outputs["cost_adjusted_mode_review_items_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/STRATEGY_MODE_COST_ADJUSTED_COMPARISON_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["strategy_mode_cost_adjusted_comparison_pack_json"].exists()
    assert "assumption_name,value,purpose" in assumptions_csv
    assert "mode_name,ledger_path,metrics_path,report_path,readiness_path" in review_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_strategy_selection_review"] is True
    assert "hqe_strategy_mode_cost_adjusted_comparison_pack.bat" in combined_docs
    assert "cost-adjusted mode comparison pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
