import json
from pathlib import Path

from src.paper_trading.strategy_tuning_baseline_pack import (
    build_and_write_strategy_tuning_baseline_report,
    build_strategy_tuning_baseline_report,
    safety_notice,
)


def _evidence(category):
    return {
        "category": category,
        "path": f"reports/{category}.json",
        "exists": True,
    }


def _review_pack(status="pass", ready=True, evidence=None, issues=None):
    if evidence is None:
        evidence = [
            _evidence("report"),
            _evidence("metrics"),
            _evidence("ledger"),
            _evidence("readiness"),
            _evidence("release_gate"),
            _evidence("operator_handoff"),
        ]

    return {
        "status": status,
        "ready_for_future_strategy_tuning_review": ready,
        "selected_dataset_path": "data/recorded/sample.csv",
        "evidence_path_count": len(evidence),
        "checklist_item_count": 10,
        "safety_notice": "paper/simulation first real backtest report review pack only",
        "issues": [] if issues is None else issues,
        "evidence_paths": evidence,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_strategy_tuning_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation strategy tuning baseline pack" in notice
    assert "safe tuning questions" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_report_review_pack_fails(tmp_path):
    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_strategy_mode_comparison is False
    assert any(issue.code == "report_review_pack_missing" for issue in report.issues)


def test_invalid_json_report_review_pack_fails(tmp_path):
    path = tmp_path / "review.json"
    path.write_text("{bad json", encoding="utf-8")

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "report_review_pack_invalid_json" for issue in report.issues)


def test_valid_review_pack_creates_strategy_tuning_baseline(tmp_path):
    path = _write_json(tmp_path / "review.json", _review_pack())

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    categories = {candidate.category for candidate in report.tuning_candidates}

    assert report.status == "pass"
    assert report.ready_for_future_strategy_mode_comparison is True
    assert report.tuning_candidate_count == 8
    assert report.evidence_category_count == 6
    assert "decision_threshold" in categories
    assert "cost_assumption" in categories


def test_warning_review_pack_fails_by_default(tmp_path):
    path = _write_json(
        tmp_path / "review.json",
        _review_pack(status="warn", ready=True),
    )

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "report_review_pack_warn" for issue in report.issues)


def test_warning_review_pack_can_remain_warning_when_allowed(tmp_path):
    path = _write_json(
        tmp_path / "review.json",
        _review_pack(status="warn", ready=True),
    )

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_strategy_mode_comparison is True


def test_not_ready_review_pack_fails(tmp_path):
    path = _write_json(
        tmp_path / "review.json",
        _review_pack(status="pass", ready=False),
    )

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "report_review_pack_not_ready" for issue in report.issues)


def test_review_pack_fail_issues_fail_baseline(tmp_path):
    path = _write_json(
        tmp_path / "review.json",
        _review_pack(
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

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "report_review_pack_contains_fail_issues" for issue in report.issues)


def test_missing_required_evidence_categories_fail(tmp_path):
    path = _write_json(
        tmp_path / "review.json",
        _review_pack(evidence=[_evidence("report"), _evidence("metrics")]),
    )

    report = build_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_tuning_evidence_categories_missing" for issue in report.issues)


def test_build_and_write_outputs_include_candidates_csv(tmp_path):
    path = _write_json(tmp_path / "review.json", _review_pack())

    report, outputs = build_and_write_strategy_tuning_baseline_report(
        report_review_pack_path=path,
        output_dir=tmp_path / "out",
    )

    text = outputs["strategy_tuning_baseline_pack_txt"].read_text(encoding="utf-8")
    candidates_csv = outputs["strategy_tuning_candidates_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["strategy_tuning_baseline_pack_json"].exists()
    assert "candidate_index,category,current_scope,review_question,safe_next_action" in candidates_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_strategy_mode_comparison"] is True


def test_docs_reference_strategy_tuning_baseline_pack():
    doc_paths = [
        Path("docs/STRATEGY_TUNING_BASELINE_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_strategy_tuning_baseline_pack.bat" in combined_docs
    assert "strategy tuning baseline pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
