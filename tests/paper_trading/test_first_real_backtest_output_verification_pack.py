import json
from pathlib import Path

from src.paper_trading.first_real_backtest_output_verification_pack import (
    build_and_write_backtest_output_verification_report,
    build_backtest_output_verification_report,
    safety_notice,
)


def _write(path: Path, text: str = "{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _first_run_pack(tmp_path, status="pass", ready=True, outputs=None, issues=None):
    dataset = _write(tmp_path / "recorded" / "sample.csv", "timestamp,open,high,low,close,volume\n")

    if outputs is None:
        outputs = [
            str(_write(tmp_path / "reports" / "inventory.json")),
            str(_write(tmp_path / "reports" / "dataset.json")),
            str(_write(tmp_path / "reports" / "quality_gate.json")),
            str(_write(tmp_path / "reports" / "backtest_trade_ledger.json")),
            str(_write(tmp_path / "reports" / "backtest_metrics.json")),
            str(_write(tmp_path / "reports" / "backtest_report.json")),
            str(_write(tmp_path / "reports" / "backtest_readiness_gate.json")),
            str(_write(tmp_path / "reports" / "v1_testing_release_gate.json")),
            str(_write(tmp_path / "reports" / "v1_testing_operator_handoff_pack.json")),
        ]

    return {
        "status": status,
        "ready_for_operator_first_real_backtest_run": ready,
        "selected_dataset_path": str(dataset),
        "expected_output_count": len(outputs),
        "expected_outputs": outputs,
        "safety_notice": "paper/simulation first real dataset backtest run pack only",
        "issues": [] if issues is None else issues,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_output_verification_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation first real backtest output verification pack" in notice
    assert "expected recorded-data paper backtest files" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_first_run_pack_fails(tmp_path):
    report = build_backtest_output_verification_report(
        first_run_pack_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_first_backtest_report_review is False
    assert any(issue.code == "first_real_backtest_run_pack_missing" for issue in report.issues)


def test_invalid_json_first_run_pack_fails(tmp_path):
    pack = tmp_path / "run_pack.json"
    pack.write_text("{bad json", encoding="utf-8")

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "first_real_backtest_run_pack_invalid_json" for issue in report.issues)


def test_valid_existing_outputs_pass(tmp_path):
    pack = _write_json(tmp_path / "run_pack.json", _first_run_pack(tmp_path))

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_first_backtest_report_review is True
    assert report.expected_output_count == 9
    assert report.existing_output_count == 9
    assert report.missing_output_count == 0
    assert any(check.category == "ledger" for check in report.output_checks)
    assert any(check.category == "metrics" for check in report.output_checks)


def test_missing_expected_outputs_fail_by_default(tmp_path):
    outputs = [
        str(tmp_path / "reports" / "missing_inventory.json"),
        str(tmp_path / "reports" / "missing_metrics.json"),
    ]
    pack = _write_json(tmp_path / "run_pack.json", _first_run_pack(tmp_path, outputs=outputs))

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.existing_output_count == 0
    assert report.missing_output_count == 2
    assert any(issue.code == "expected_backtest_outputs_missing_on_disk" for issue in report.issues)


def test_output_existence_check_can_be_skipped(tmp_path):
    outputs = [
        str(tmp_path / "reports" / "missing_inventory.json"),
        str(tmp_path / "reports" / "missing_metrics.json"),
    ]
    pack = _write_json(tmp_path / "run_pack.json", _first_run_pack(tmp_path, outputs=outputs))

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
        require_expected_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.ready_for_future_first_backtest_report_review is True
    assert report.missing_output_count == 2


def test_warning_first_run_pack_fails_by_default(tmp_path):
    pack = _write_json(
        tmp_path / "run_pack.json",
        _first_run_pack(tmp_path, status="warn", ready=True),
    )

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "first_real_backtest_run_pack_warn" for issue in report.issues)


def test_warning_first_run_pack_can_remain_warning_when_allowed(tmp_path):
    pack = _write_json(
        tmp_path / "run_pack.json",
        _first_run_pack(tmp_path, status="warn", ready=True),
    )

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_first_backtest_report_review is True


def test_not_ready_first_run_pack_fails(tmp_path):
    pack = _write_json(
        tmp_path / "run_pack.json",
        _first_run_pack(tmp_path, status="pass", ready=False),
    )

    report = build_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "first_real_backtest_run_pack_not_ready" for issue in report.issues)


def test_build_and_write_outputs_include_checks_csv(tmp_path):
    pack = _write_json(tmp_path / "run_pack.json", _first_run_pack(tmp_path))

    report, outputs = build_and_write_backtest_output_verification_report(
        first_run_pack_path=pack,
        output_dir=tmp_path / "out",
    )

    text = outputs["first_real_backtest_output_verification_pack_txt"].read_text(encoding="utf-8")
    checks_csv = outputs["first_real_backtest_output_checks_csv"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["first_real_backtest_output_verification_pack_json"].exists()
    assert "output_index,category,required,exists,output_path" in checks_csv
    assert "not a profitability claim" in text.lower()
    assert manifest["ready_for_future_first_backtest_report_review"] is True


def test_docs_reference_first_real_backtest_output_verification_pack():
    doc_paths = [
        Path("docs/FIRST_REAL_BACKTEST_OUTPUT_VERIFICATION_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)

    assert "hqe_first_real_backtest_output_verification_pack.bat" in combined_docs
    assert "first real backtest output verification pack" in combined_docs.lower()
    assert "not a profitability claim" in combined_docs.lower()
