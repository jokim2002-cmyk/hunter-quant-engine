import json
from pathlib import Path

from src.paper_trading.recorded_data_paper_strategy_adapter_contract_acceptance import (
    build_adapter_contract_acceptance_report,
    build_and_write_adapter_contract_acceptance_report,
    safety_notice,
)


def _request(planned_bar_count=2):
    return {
        "request_id": "paper_strategy_adapter_request_001",
        "scenario_id": "recorded_strategy_replay_scenario_001",
        "source_path": "sample.csv",
        "source_type": "csv",
        "planned_bar_count": planned_bar_count,
        "first_timestamp": "2026-01-01T09:15:00+05:30",
        "last_timestamp": "2026-01-01T09:16:00+05:30",
        "adapter_mode": "contract_only_no_strategy_execution",
        "strategy_execution_mode": "not_executed_contract_only",
        "broker_execution_mode": "broker_disabled",
        "output_mode": "adapter_request_manifest_only",
    }


def _contract(status="pass", ready=True, requests=None):
    adapter_requests = requests if requests is not None else [_request()]
    return {
        "status": status,
        "ready_for_future_adapter": ready,
        "request_count": len(adapter_requests),
        "total_planned_bars": sum(
            request.get("planned_bar_count", 0) for request in adapter_requests
        ),
        "adapter_requests": adapter_requests,
    }


def _write_contract(tmp_path, payload):
    path = tmp_path / "paper_strategy_adapter_contract.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_safety_notice_preserves_adapter_contract_acceptance_boundary():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not execute strategy logic" in notice
    assert "create signals" in notice
    assert "calculate pnl" in notice
    assert "prove profitability" in notice


def test_missing_adapter_contract_fails(tmp_path):
    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_contract_missing" for issue in report.issues)


def test_invalid_json_fails(tmp_path):
    path = tmp_path / "paper_strategy_adapter_contract.json"
    path.write_text("{bad-json", encoding="utf-8")

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_contract_invalid_json" for issue in report.issues)


def test_valid_contract_is_accepted(tmp_path):
    path = _write_contract(tmp_path, _contract())

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.request_count == 1
    assert report.total_planned_bars == 2


def test_not_ready_contract_fails(tmp_path):
    path = _write_contract(tmp_path, _contract(status="pass", ready=False))

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_contract_not_ready" for issue in report.issues)


def test_warn_contract_fails_by_default(tmp_path):
    path = _write_contract(tmp_path, _contract(status="warn", ready=True))

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "adapter_contract_warn" for issue in report.issues)


def test_warn_contract_can_be_accepted_when_allowed(tmp_path):
    path = _write_contract(tmp_path, _contract(status="warn", ready=True))

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
        allow_warnings=True,
    )

    assert report.status == "warn"
    assert report.accepted is True


def test_min_request_rule_can_fail(tmp_path):
    path = _write_contract(tmp_path, _contract())

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
        min_requests=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_adapter_requests" for issue in report.issues)


def test_min_total_bars_rule_can_fail(tmp_path):
    path = _write_contract(tmp_path, _contract(requests=[_request(planned_bar_count=1)]))

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
        min_total_planned_bars=2,
    )

    assert report.status == "fail"
    assert any(issue.code == "insufficient_total_planned_bars" for issue in report.issues)


def test_wrong_modes_and_forbidden_fields_fail(tmp_path):
    request = _request()
    request["adapter_mode"] = "execute"
    request["order_id"] = "not-allowed"
    path = _write_contract(tmp_path, _contract(requests=[request]))

    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
    )

    assert report.status == "fail"
    assert any(issue.code == "adapter_request_wrong_modes" for issue in report.issues)
    assert any(issue.code == "adapter_request_forbidden_fields" for issue in report.issues)


def test_build_and_write_acceptance_outputs_safety_and_no_profit_claim(tmp_path):
    path = _write_contract(tmp_path, _contract())

    report, outputs = build_and_write_adapter_contract_acceptance_report(
        adapter_contract_path=path,
        output_dir=tmp_path / "out",
    )

    text_report = outputs["paper_strategy_adapter_contract_acceptance_txt"].read_text(
        encoding="utf-8"
    )
    manifest = json.loads(outputs["manifest_json"].read_text(encoding="utf-8"))

    assert report.status == "pass"
    assert outputs["paper_strategy_adapter_contract_acceptance_json"].exists()
    assert outputs["paper_strategy_adapter_contract_acceptance_txt"].exists()
    assert "not a profitability claim" in text_report
    assert manifest["accepted"] is True


def test_documentation_mentions_adapter_contract_acceptance_shortcut():
    doc_paths = [
        Path("docs/RECORDED_DATA_PAPER_STRATEGY_ADAPTER_CONTRACT_ACCEPTANCE.md"),
        Path("README.md"),
        Path("ROADMAP.md"),
    ]

    for doc_path in doc_paths:
        assert doc_path.exists(), f"Missing documentation file: {doc_path}"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    assert "hqe_recorded_data_paper_strategy_adapter_contract_acceptance.bat" in combined
    assert "paper/simulation" in combined.lower()
    assert "not a profitability claim" in combined.lower()
