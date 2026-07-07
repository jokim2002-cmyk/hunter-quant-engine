import json
from pathlib import Path

from src.paper_trading.strategy_mode_comparison_pack import (
    build_and_write_strategy_mode_comparison_report,
    build_strategy_mode_comparison_report,
    safety_notice,
)


CATEGORIES = [
    "decision_threshold",
    "max_holding_bars",
    "stop_loss_points",
    "target_points",
    "neutral_filter",
    "quality_filter",
    "cost_assumption",
    "session_window",
]


def _candidate(category):
    return {
        "candidate_index": 1,
        "category": category,
        "current_scope": f"{category} scope",
        "review_question": f"{category} question",
        "safe_next_action": f"{category} action",
    }


def _baseline(status="pass", ready=True, categories=None, issues=None):
    if categories is None:
        categories = CATEGORIES

    return {
        "status": status,
        "ready_for_future_strategy_mode_comparison": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "tuning_candidate_count": len(categories),
        "evidence_category_count": 6,
        "safety_notice": "paper/simulation strategy tuning baseline pack only",
        "issues": [] if issues is None else issues,
        "tuning_candidates": [_candidate(category) for category in categories],
        "evidence_categories": [
            "report",
            "metrics",
            "ledger",
            "readiness",
            "release_gate",
            "operator_handoff",
        ],
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_strategy_mode_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation strategy mode comparison pack" in notice
    assert "strict, balanced, and relaxed" in notice
    assert "does not modify strategy logic" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_baseline_pack_fails(tmp_path):
    report = build_strategy_mode_comparison_report(
        baseline_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_paper_mode_backtest is False
    assert any(issue.code == "strategy_tuning_baseline_pack_missing" for issue in report.issues)


def test_invalid_json_baseline_pack_fails(tmp_path):
    path = tmp_path / "baseline.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_tuning_baseline_pack_invalid_json" for issue in report.issues)


def test_valid_baseline_creates_three_modes(tmp_path):
    path = _write_json(tmp_path / "baseline.json", _baseline())

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    mode_names = {mode.mode_name for mode in report.modes}

    assert report.status == "pass"
    assert report.ready_for_future_paper_mode_backtest is True
    assert report.mode_count == 3
    assert mode_names == {"strict", "balanced", "relaxed"}
    assert report.tuning_candidate_count == 8


def test_mode_parameters_are_ordered_from_strict_to_relaxed(tmp_path):
    path = _write_json(tmp_path / "baseline.json", _baseline())

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    modes = {mode.mode_name: mode for mode in report.modes}

    assert modes["strict"].decision_threshold > modes["balanced"].decision_threshold
    assert modes["balanced"].decision_threshold > modes["relaxed"].decision_threshold
    assert modes["strict"].max_holding_bars < modes["balanced"].max_holding_bars
    assert modes["balanced"].max_holding_bars < modes["relaxed"].max_holding_bars


def test_warning_baseline_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "baseline.json",
        _baseline(status="warn", ready=True),
    )

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_tuning_baseline_pack_warn" for issue in report.issues)


def test_warning_baseline_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "baseline.json",
        _baseline(status="warn", ready=True),
    )

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_paper_mode_backtest is True


def test_not_ready_baseline_fails(tmp_path):
    path = _write_json(
        tmp_path / "baseline.json",
        _baseline(status="pass", ready=False),
    )

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_tuning_baseline_pack_not_ready" for issue in report.issues)


def test_missing_required_candidate_categories_fail(tmp_path):
    path = _write_json(
        tmp_path / "baseline.json",
        _baseline(categories=["decision_threshold", "max_holding_bars"]),
    )

    report = build_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_strategy_mode_candidate_categories_missing" for issue in report.issues)


def test_build_and_write_outputs_include_modes_csv(tmp_path):
    path = _write_json(tmp_path / "baseline.json", _baseline())

    report, outputs = build_and_write_strategy_mode_comparison_report(
        baseline_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["strategy_mode_comparison_pack_txt"].read_text(encoding="utf-8")
    modes_csv = outputs["strategy_mode_definitions_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["strategy_mode_comparison_pack_json"].exists()
    assert "mode_name,description,decision_threshold,max_holding_bars" in modes_csv
    assert "strict" in modes_csv
    assert "balanced" in modes_csv
    assert "relaxed" in modes_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_paper_mode_backtest"] is True


def test_docs_reference_strategy_mode_comparison_pack():
    doc_paths = [
        Path("docs/STRATEGY_MODE_COMPARISON_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_strategy_mode_comparison_pack.bat" in combined_docs
    assert "strategy mode comparison pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
