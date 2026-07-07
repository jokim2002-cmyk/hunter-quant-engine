import json
from pathlib import Path

from src.paper_trading.v1_testing_operator_handoff_pack import (
    build_and_write_operator_handoff_pack_report,
    build_operator_handoff_pack_report,
    safety_notice,
)


def _gate(tmp_path, status="pass", accepted=True, final_outputs=True, issues=None):
    final_report = tmp_path / "backtest_report.txt"
    final_metrics = tmp_path / "backtest_metrics.json"
    final_ledger = tmp_path / "backtest_trade_ledger.json"

    if final_outputs:
        final_report.write_text("paper report\nnot a profitability claim\n", encoding="utf-8")
        final_metrics.write_text("{}", encoding="utf-8")
        final_ledger.write_text("{}", encoding="utf-8")

    return {
        "status": status,
        "accepted_for_future_v1_testing_release_close": accepted,
        "final_backtest_report_path": str(final_report),
        "final_metrics_path": str(final_metrics),
        "final_trade_ledger_path": str(final_ledger),
        "safety_notice": "paper/simulation v1.0 testing edition release gate only",
        "issues": [] if issues is None else issues,
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_operator_handoff_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation v1.0 testing edition operator handoff" in notice
    assert "recorded replay paper backtest evidence" in notice
    assert "does not connect to brokers" in notice
    assert "real money" in notice
    assert "prove profitability" in notice


def test_missing_v1_testing_release_gate_fails(tmp_path):
    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.ready_for_future_v1_release_notes is False
    assert any(issue.code == "v1_testing_release_gate_missing" for issue in report.issues)


def test_valid_v1_gate_creates_operator_handoff_pack(tmp_path):
    gate = _write_json(tmp_path / "gate.json", _gate(tmp_path))

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.ready_for_future_v1_release_notes is True
    assert report.release_gate_status == "pass"
    assert report.release_gate_accepted is True
    assert report.checklist_item_count == 10
    assert any("CE BUY" in item.action for item in report.checklist)
    assert any("PE BUY" in item.action for item in report.checklist)


def test_warning_gate_fails_by_default(tmp_path):
    gate = _write_json(
        tmp_path / "gate.json",
        _gate(tmp_path, status="warn", accepted=True),
    )

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "v1_testing_release_gate_warn" for issue in report.issues)


def test_warning_gate_can_remain_warning_when_allowed(tmp_path):
    gate = _write_json(
        tmp_path / "gate.json",
        _gate(tmp_path, status="warn", accepted=True),
    )

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.ready_for_future_v1_release_notes is True


def test_not_accepted_gate_fails(tmp_path):
    gate = _write_json(
        tmp_path / "gate.json",
        _gate(tmp_path, status="pass", accepted=False),
    )

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "v1_testing_release_gate_not_accepted" for issue in report.issues)


def test_missing_final_output_paths_fail(tmp_path):
    payload = _gate(tmp_path)
    payload["final_backtest_report_path"] = ""
    gate = _write_json(tmp_path / "gate.json", payload)

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "final_output_paths_missing" for issue in report.issues)


def test_final_outputs_missing_on_disk_fail_by_default(tmp_path):
    gate = _write_json(
        tmp_path / "gate.json",
        _gate(tmp_path, final_outputs=False),
    )

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "final_outputs_missing_on_disk" for issue in report.issues)


def test_final_output_existence_check_can_be_skipped(tmp_path):
    gate = _write_json(
        tmp_path / "gate.json",
        _gate(tmp_path, final_outputs=False),
    )

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
        require_final_outputs_exist=False,
    )

    assert report.status == "pass"
    assert report.ready_for_future_v1_release_notes is True


def test_release_gate_fail_issues_fail_handoff(tmp_path):
    gate = _write_json(
        tmp_path / "gate.json",
        _gate(
            tmp_path,
            issues=[
                {
                    "severity": "fail",
                    "code": "example_fail",
                    "count": 1,
                    "message": "example",
                }
            ],
        ),
    )

    report = build_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "release_gate_contains_fail_issues" for issue in report.issues)


def test_build_and_write_outputs_and_docs_reference_operator_handoff_pack(tmp_path):
    gate = _write_json(tmp_path / "gate.json", _gate(tmp_path))

    report, outputs = build_and_write_operator_handoff_pack_report(
        v1_testing_release_gate_path=gate,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["v1_testing_operator_handoff_pack_txt"].read_text(encoding="utf-8")
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    doc_paths = [
        Path("docs/V1_TESTING_OPERATOR_HANDOFF_PACK.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]
    combined_docs = "\n".join(doc.read_text(encoding="utf-8") for doc in doc_paths)

    assert report.status == "pass"
    assert outputs["v1_testing_operator_handoff_pack_json"].exists()
    assert outputs["v1_testing_operator_checklist_csv"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["ready_for_future_v1_release_notes"] is True
    assert "hqe_v1_testing_operator_handoff_pack.bat" in combined_docs
    assert "paper-only v1.0 testing operator handoff" in combined_docs
    assert "not a profitability claim" in combined_docs.lower()
