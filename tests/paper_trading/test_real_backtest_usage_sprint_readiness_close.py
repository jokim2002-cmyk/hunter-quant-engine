import json
from pathlib import Path

from src.paper_trading.real_backtest_usage_sprint_readiness_close import (
    build_and_write_real_backtest_usage_sprint_readiness_close_report,
    build_real_backtest_usage_sprint_readiness_close_report,
    safety_notice,
)


MODES = ["strict", "balanced", "relaxed"]
ASSUMPTIONS = [
    "brokerage_reference",
    "slippage_reference",
    "taxes_and_charges_reference",
    "round_trip_cost_formula",
]


def _assumption(name):
    return {
        "assumption_name": name,
        "value": "operator_supplied",
        "purpose": f"{name} purpose",
    }


def _review_item(mode):
    return {
        "mode_name": mode,
        "ledger_path": f"reports/{mode}/ledger.json",
        "metrics_path": f"reports/{mode}/metrics.json",
        "report_path": f"reports/{mode}/report.json",
        "readiness_path": f"reports/{mode}/readiness.json",
        "cost_review_status": "requires_operator_cost_inputs",
        "review_instruction": "review only",
    }


def _cost_pack(status="pass", ready=True, modes=None, assumptions=None, issues=None):
    if modes is None:
        modes = MODES
    if assumptions is None:
        assumptions = ASSUMPTIONS

    return {
        "status": status,
        "ready_for_future_strategy_selection_review": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "mode_count": len(modes),
        "cost_assumption_count": len(assumptions),
        "review_item_count": len(modes),
        "safety_notice": "paper/simulation cost-adjusted mode comparison pack only",
        "issues": [] if issues is None else issues,
        "mode_names": modes,
        "cost_assumptions": [_assumption(name) for name in assumptions],
        "review_items": [_review_item(mode) for mode in modes],
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_phase_1_close_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation real backtest usage sprint readiness close" in notice
    assert "does not run backtests" in notice
    assert "does not calculate profitability" in notice
    assert "does not select a winning strategy" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_cost_adjusted_pack_fails(tmp_path):
    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.phase_1_closed is False
    assert any(issue.code == "cost_adjusted_mode_comparison_pack_missing" for issue in report.issues)


def test_invalid_json_cost_adjusted_pack_fails(tmp_path):
    path = tmp_path / "cost.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "cost_adjusted_mode_comparison_pack_invalid_json" for issue in report.issues)


def test_valid_cost_adjusted_pack_closes_phase_1(tmp_path):
    path = _write_json(tmp_path / "cost.json", _cost_pack())

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.phase_1_closed is True
    assert report.ready_for_future_dashboard_sprint is True
    assert report.completed_total_before_module == 72
    assert report.completed_total_after_module == 73
    assert report.phase_1_pending_after_module == 0
    assert report.full_hqe_product_estimate_after_module == "65-70%"


def test_warning_cost_adjusted_pack_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "cost.json",
        _cost_pack(status="warn", ready=True),
    )

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "cost_adjusted_mode_comparison_pack_warn" for issue in report.issues)


def test_warning_cost_adjusted_pack_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "cost.json",
        _cost_pack(status="warn", ready=True),
    )

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.phase_1_closed is True
    assert report.ready_for_future_dashboard_sprint is True


def test_not_ready_cost_adjusted_pack_fails(tmp_path):
    path = _write_json(
        tmp_path / "cost.json",
        _cost_pack(status="pass", ready=False),
    )

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "cost_adjusted_mode_comparison_pack_not_ready" for issue in report.issues)


def test_pack_fail_issues_fail_close(tmp_path):
    path = _write_json(
        tmp_path / "cost.json",
        _cost_pack(
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

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "cost_adjusted_mode_comparison_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_modes_fail(tmp_path):
    path = _write_json(
        tmp_path / "cost.json",
        _cost_pack(modes=["strict", "balanced"]),
    )

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "phase_1_required_modes_missing" for issue in report.issues)


def test_missing_required_cost_assumptions_fail(tmp_path):
    path = _write_json(
        tmp_path / "cost.json",
        _cost_pack(assumptions=["brokerage_reference", "slippage_reference"]),
    )

    report = build_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "phase_1_required_cost_assumptions_missing" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_close(tmp_path):
    path = _write_json(tmp_path / "cost.json", _cost_pack())

    report, outputs = build_and_write_real_backtest_usage_sprint_readiness_close_report(
        cost_adjusted_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["real_backtest_usage_sprint_readiness_close_txt"].read_text(encoding="utf-8")
    checklist = json.loads(outputs["real_backtest_usage_sprint_checklist_json"].read_text(encoding="utf-8"))
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/REAL_BACKTEST_USAGE_SPRINT_READINESS_CLOSE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert report.status == "pass"
    assert outputs["real_backtest_usage_sprint_readiness_close_json"].exists()
    assert checklist["checklist_item_count"] == report.checklist_item_count
    assert "Phase 1 closed: True" in text
    assert "not a profitability claim" in text.lower()
    assert manifest["phase_1_closed"] is True
    assert "hqe_real_backtest_usage_sprint_readiness_close.bat" in combined_docs
    assert "real backtest usage sprint readiness close" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
