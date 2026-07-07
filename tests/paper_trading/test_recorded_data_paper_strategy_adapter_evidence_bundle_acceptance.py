import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_evidence_bundle_acceptance import (
    build_adapter_evidence_bundle_acceptance_report,
    build_and_write_adapter_evidence_bundle_acceptance_report,
    safety_notice,
)


def _stage(name, status="pass", accepted=True):
    return {
        "stage": name,
        "status": status,
        "output_directory": f"reports/{name}",
        "output_files": {"report": f"reports/{name}/report.json"},
        "accepted": accepted,
        "summary": {"message": "ok"},
    }


def _bundle(status="pass", ready=True, stages=None):
    stage_results = stages if stages is not None else [
        _stage("recorded_data_paper_strategy_adapter_readiness"),
        _stage("recorded_data_paper_strategy_adapter_dry_run_readiness"),
    ]
    return {
        "status": status,
        "ready_for_future_adapter_evidence": ready,
        "stage_results": stage_results,
        "safety_notice": "paper/simulation only",
    }


def _write_bundle(tmp_path, payload):
    path = tmp_path / "paper_strategy_adapter_evidence_bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_adapter_evidence_bundle_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_adapter_evidence_bundle_fails(tmp_path):
    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_evidence_bundle_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "paper_strategy_adapter_evidence_bundle.json"
    path.write_text("{bad-json", encoding="utf-8")

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_evidence_bundle_invalid_json" for issue in report.issues)


def test_valid_bundle_is_accepted(tmp_path):
    path = _write_bundle(tmp_path, _bundle())

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.stage_count == 2


def test_not_ready_bundle_fails(tmp_path):
    path = _write_bundle(tmp_path, _bundle(status="pass", ready=False))

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_evidence_bundle_not_ready" for issue in report.issues)


def test_warn_bundle_fails_by_default(tmp_path):
    path = _write_bundle(tmp_path, _bundle(status="warn", ready=True))

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_evidence_bundle_warn" for issue in report.issues)


def test_warn_bundle_can_be_accepted_when_allowed(tmp_path):
    path = _write_bundle(tmp_path, _bundle(status="warn", ready=True))

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True


def test_missing_required_stage_fails(tmp_path):
    path = _write_bundle(
        tmp_path,
        _bundle(stages=[_stage("recorded_data_paper_strategy_adapter_readiness")]),
    )

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "adapter_evidence_bundle_missing_required_stages"
        for issue in report.issues
    )


def test_stage_not_accepted_or_wrong_status_fails(tmp_path):
    path = _write_bundle(
        tmp_path,
        _bundle(
            stages=[
                _stage("recorded_data_paper_strategy_adapter_readiness", accepted=False),
                _stage("recorded_data_paper_strategy_adapter_dry_run_readiness", status="fail"),
            ]
        ),
    )

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_evidence_stage_not_accepted" for issue in report.issues)
    assert any(issue.code == "adapter_evidence_stage_invalid_status" for issue in report.issues)


def test_forbidden_fields_fail_bundle(tmp_path):
    payload = _bundle()
    payload["order_id"] = "not-allowed"
    path = _write_bundle(tmp_path, payload)

    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_evidence_bundle_forbidden_fields" for issue in report.issues)


def test_build_and_write_acceptance_outputs_safety_and_no_profit_claim(tmp_path):
    path = _write_bundle(tmp_path, _bundle())

    report, outputs = build_and_write_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=path,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_adapter_evidence_bundle_acceptance_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_evidence_bundle_acceptance_json"].exists()
    assert outputs["paper_strategy_adapter_evidence_bundle_acceptance_txt"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted"] is True


def test_documentation_mentions_adapter_evidence_bundle_acceptance_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_EVIDENCE_BUNDLE_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_evidence_bundle_acceptance.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
