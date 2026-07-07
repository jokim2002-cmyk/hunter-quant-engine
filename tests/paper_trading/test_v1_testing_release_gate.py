import json
from pathlib import Path

from src.paper_trading.v1_testing_release_gate import (
    build_and_write_v1_testing_release_gate_report,
    build_v1_testing_release_gate_report,
    safety_notice,
)


def _stage(name, status="pass", ready=True):
    return {
        "stage_name": name,
        "status": status,
        "ready": ready,
        "primary_output": f"out/{name}.json",
        "detail": f"{name} status={status}, ready={ready}",
    }


def _release_doc(tmp_path, text=None):
    path = tmp_path / "V0_6_RECORDED_DATA_BACKTEST_READINESS_RELEASE.md"
    path.write_text(
        text
        or "\n".join(
            [
                "v0.6-recorded-data-backtest-readiness",
                "paper-only backtest readiness gate",
                "LONG = CE BUY paper plan only",
                "SHORT = PE BUY paper plan only",
                "NEUTRAL = no trade",
                "No option selling",
                "No broker orders",
                "No real money",
                "No profitability claim",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _readiness(tmp_path, status="pass", ready=True, stages=None, final_outputs=True):
    final_report = tmp_path / "backtest_report.txt"
    final_metrics = tmp_path / "backtest_metrics.json"
    final_ledger = tmp_path / "backtest_trade_ledger.json"

    if final_outputs:
        final_report.write_text("paper report\nnot a profitability claim\n", encoding="utf-8")
        final_metrics.write_text("{}", encoding="utf-8")
        final_ledger.write_text("{}", encoding="utf-8")

    if stages is None:
        stages = [
            _stage("one_command_backtest_runner"),
            _stage("backtest_acceptance_gate"),
        ]

    return {
        "status": status,
        "ready_for_future_v1_testing_release_gate": ready,
        "stage_count": len(stages),
        "passed_stage_count": sum(1 for stage in stages if stage["status"] == "pass"),
        "warning_stage_count": sum(1 for stage in stages if stage["status"] == "warn"),
        "failed_stage_count": sum(1 for stage in stages if stage["status"] == "fail"),
        "final_backtest_report_path": str(final_report),
        "final_metrics_path": str(final_metrics),
        "final_trade_ledger_path": str(final_ledger),
        "safety_notice": "paper/simulation backtest readiness gate only",
        "stages": stages,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_v1_testing_gate_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation v1.0 testing edition release gate" in notice
    assert "recorded replay paper backtest readiness evidence" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_backtest_readiness_fails(tmp_path):
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=tmp_path / "missing.json",
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted_for_future_v1_testing_release_close is False
    assert any(issue.code == "backtest_readiness_missing" for issue in report.issues)


def test_missing_release_doc_fails(tmp_path):
    readiness = _write_json(tmp_path / "readiness.json", _readiness(tmp_path))

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=tmp_path / "missing.md",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "release_doc_missing" for issue in report.issues)


def test_valid_backtest_readiness_is_accepted(tmp_path):
    readiness = _write_json(tmp_path / "readiness.json", _readiness(tmp_path))
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted_for_future_v1_testing_release_close is True
    assert report.readiness_stage_count == 2
    assert report.readiness_passed_stage_count == 2
    assert report.readiness_failed_stage_count == 0
    assert report.final_backtest_report_path.endswith("backtest_report.txt")


def test_warning_readiness_fails_by_default(tmp_path):
    stages = [
        _stage("one_command_backtest_runner", status="warn", ready=True),
        _stage("backtest_acceptance_gate", status="warn", ready=True),
    ]
    readiness = _write_json(
        tmp_path / "readiness.json",
        _readiness(tmp_path, status="warn", ready=True, stages=stages),
    )
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "backtest_readiness_warn" for issue in report.issues)


def test_warning_readiness_can_remain_warning_when_allowed(tmp_path):
    stages = [
        _stage("one_command_backtest_runner", status="warn", ready=True),
        _stage("backtest_acceptance_gate", status="warn", ready=True),
    ]
    readiness = _write_json(
        tmp_path / "readiness.json",
        _readiness(tmp_path, status="warn", ready=True, stages=stages),
    )
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted_for_future_v1_testing_release_close is True


def test_not_ready_readiness_fails(tmp_path):
    readiness = _write_json(
        tmp_path / "readiness.json",
        _readiness(tmp_path, status="pass", ready=False),
    )
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "backtest_readiness_not_ready" for issue in report.issues)


def test_missing_expected_readiness_stage_fails(tmp_path):
    readiness = _write_json(
        tmp_path / "readiness.json",
        _readiness(tmp_path, stages=[_stage("one_command_backtest_runner")]),
    )
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_readiness_stages" for issue in report.issues)
    assert any(issue.code == "expected_readiness_stages_missing" for issue in report.issues)


def test_final_outputs_missing_on_disk_fails_by_default(tmp_path):
    readiness = _write_json(
        tmp_path / "readiness.json",
        _readiness(tmp_path, final_outputs=False),
    )
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "final_backtest_outputs_missing_on_disk" for issue in report.issues)


def test_final_output_existence_check_can_be_skipped(tmp_path):
    readiness = _write_json(
        tmp_path / "readiness.json",
        _readiness(tmp_path, final_outputs=False),
    )
    release_doc = _release_doc(tmp_path)

    report = build_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
        require_final_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.accepted_for_future_v1_testing_release_close is True


def test_build_and_write_outputs_and_docs_reference_v1_gate(tmp_path):
    readiness = _write_json(tmp_path / "readiness.json", _readiness(tmp_path))
    release_doc = _release_doc(tmp_path)

    report, outputs = build_and_write_v1_testing_release_gate_report(
        backtest_readiness_path=readiness,
        release_doc_path=release_doc,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["v1_testing_release_gate_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/V1_TESTING_RELEASE_GATE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["v1_testing_release_gate_json"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted_for_future_v1_testing_release_close"] is True
    assert "hqe_v1_testing_release_gate.bat" in combined_docs
    assert "paper-only v1.0 testing release gate" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
