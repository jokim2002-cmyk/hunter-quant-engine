import json
from pathlib import Path

from src.paper_trading.first_real_backtest_report_review_pack import (
    build_and_write_first_backtest_report_review_pack,
    build_first_backtest_report_review_pack,
    safety_notice,
)


def _write(path: Path, text: str = "{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _check(category, path):
    return {
        "output_index": 1,
        "output_path": str(path),
        "exists": True,
        "category": category,
        "required": True,
    }


def _verification(tmp_path, status="pass", ready=True, checks=None, issues=None):
    dataset = _write(tmp_path / "recorded" / "sample.csv", "timestamp,open,high,low,close,volume\n")

    if checks is None:
        checks = [
            _check("ledger", _write(tmp_path / "reports" / "backtest_trade_ledger.json")),
            _check("metrics", _write(tmp_path / "reports" / "backtest_metrics.json")),
            _check("report", _write(tmp_path / "reports" / "backtest_report.json")),
            _check("readiness", _write(tmp_path / "reports" / "backtest_readiness_gate.json")),
            _check("release_gate", _write(tmp_path / "reports" / "v1_testing_release_gate.json")),
            _check("operator_handoff", _write(tmp_path / "reports" / "v1_testing_operator_handoff_pack.json")),
        ]

    return {
        "status": status,
        "ready_for_future_first_backtest_report_review": ready,
        "selected_dataset_path": str(dataset),
        "expected_output_count": len(checks),
        "existing_output_count": len(checks),
        "missing_output_count": 0,
        "safety_notice": "paper/simulation first real backtest output verification pack only",
        "issues": [] if issues is None else issues,
        "output_checks": checks,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_report_review_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation first real backtest report review pack" in notice
    assert "recorded-data paper backtest outputs" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_verification_pack_fails(tmp_path):
    report = build_first_backtest_report_review_pack(
        verification_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_strategy_tuning_review is False
    assert any(issue.code == "output_verification_pack_missing" for issue in report.issues)


def test_invalid_json_verification_pack_fails(tmp_path):
    pack = tmp_path / "verification.json"
    pack.write_text("{bad json", encoding="utf-8")

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "output_verification_pack_invalid_json" for issue in report.issues)


def test_valid_verification_pack_creates_review_pack(tmp_path):
    pack = _write_json(tmp_path / "verification.json", _verification(tmp_path))

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_strategy_tuning_review is True
    assert report.evidence_path_count == 6
    assert report.checklist_item_count == 10
    assert any(path.category == "ledger" for path in report.evidence_paths)
    assert any(item.category == "strategy_review" for item in report.checklist)


def test_warning_verification_pack_fails_by_default(tmp_path):
    pack = _write_json(
        tmp_path / "verification.json",
        _verification(tmp_path, status="warn", ready=True),
    )

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "output_verification_pack_warn" for issue in report.issues)


def test_warning_verification_pack_can_remain_warning_when_allowed(tmp_path):
    pack = _write_json(
        tmp_path / "verification.json",
        _verification(tmp_path, status="warn", ready=True),
    )

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_strategy_tuning_review is True


def test_not_ready_verification_pack_fails(tmp_path):
    pack = _write_json(
        tmp_path / "verification.json",
        _verification(tmp_path, status="pass", ready=False),
    )

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "output_verification_pack_not_ready" for issue in report.issues)


def test_missing_required_review_categories_fail(tmp_path):
    checks = [
        _check("ledger", _write(tmp_path / "reports" / "backtest_trade_ledger.json")),
        _check("metrics", _write(tmp_path / "reports" / "backtest_metrics.json")),
    ]
    pack = _write_json(tmp_path / "verification.json", _verification(tmp_path, checks=checks))

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_review_evidence_categories_missing" for issue in report.issues)


def test_missing_evidence_files_fail_by_default(tmp_path):
    missing_path = tmp_path / "reports" / "missing_backtest_report.json"
    checks = [
        _check("ledger", _write(tmp_path / "reports" / "backtest_trade_ledger.json")),
        _check("metrics", _write(tmp_path / "reports" / "backtest_metrics.json")),
        _check("report", missing_path),
        _check("readiness", _write(tmp_path / "reports" / "backtest_readiness_gate.json")),
        _check("release_gate", _write(tmp_path / "reports" / "v1_testing_release_gate.json")),
        _check("operator_handoff", _write(tmp_path / "reports" / "v1_testing_operator_handoff_pack.json")),
    ]
    pack = _write_json(tmp_path / "verification.json", _verification(tmp_path, checks=checks))

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "required_review_evidence_files_missing_on_disk" for issue in report.issues)


def test_evidence_existence_check_can_be_skipped(tmp_path):
    missing_path = tmp_path / "reports" / "missing_backtest_report.json"
    checks = [
        _check("ledger", _write(tmp_path / "reports" / "backtest_trade_ledger.json")),
        _check("metrics", _write(tmp_path / "reports" / "backtest_metrics.json")),
        _check("report", missing_path),
        _check("readiness", _write(tmp_path / "reports" / "backtest_readiness_gate.json")),
        _check("release_gate", _write(tmp_path / "reports" / "v1_testing_release_gate.json")),
        _check("operator_handoff", _write(tmp_path / "reports" / "v1_testing_operator_handoff_pack.json")),
    ]
    pack = _write_json(tmp_path / "verification.json", _verification(tmp_path, checks=checks))

    report = build_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
        require_evidence_exists=False,
    )

    assert report.status == "pass"
    assert report.ready_for_future_strategy_tuning_review is True


def test_build_and_write_outputs_include_review_csvs(tmp_path):
    pack = _write_json(tmp_path / "verification.json", _verification(tmp_path))

    report, outputs = build_and_write_first_backtest_report_review_pack(
        verification_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    text = outputs["first_real_backtest_report_review_pack_txt"].read_text(encoding="utf-8")
    checklist_csv = outputs["first_real_backtest_report_review_checklist_csv"].read_text(encoding="utf-8")
    evidence_csv = outputs["first_real_backtest_report_review_evidence_paths_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["first_real_backtest_report_review_pack_json"].exists()
    assert "item_index,category,required,action,expected_result" in checklist_csv
    assert "category,exists,path" in evidence_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_strategy_tuning_review"] is True


def test_docs_reference_first_real_backtest_report_review_pack():
    doc_paths = [
        Path("docs/FIRST_REAL_BACKTEST_REPORT_REVIEW_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_first_real_backtest_report_review_pack.bat" in combined_docs
    assert "first real backtest report review pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
