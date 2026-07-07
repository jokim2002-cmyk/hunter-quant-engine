import json
from pathlib import Path

from src.paper_trading.recorded_data_backtest_dependency_bridge import (
    build_and_write_dependency_bridge_report,
    build_dependency_bridge_report,
    safety_notice,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_bridge_passes_from_strategy_input_contract(tmp_path):
    contract = tmp_path / "strategy_input_contract.json"
    bars = tmp_path / "strategy_input_bars.jsonl"
    output_dir = tmp_path / "readiness"
    bundle_dir = tmp_path / "bundle"
    acceptance_dir = tmp_path / "acceptance"

    _write_json(
        contract,
        {
            "status": "pass",
            "input_event_count": 3,
            "accepted_bar_count": 3,
        },
    )
    _write_jsonl(
        bars,
        [
            {"bar_index": 1, "timestamp": "2026-01-01T09:15:00", "close": 100.0},
            {"bar_index": 2, "timestamp": "2026-01-01T09:20:00", "close": 101.0},
            {"bar_index": 3, "timestamp": "2026-01-01T09:25:00", "close": 102.0},
        ],
    )

    report, outputs = build_and_write_dependency_bridge_report(
        strategy_input_contract_path=contract,
        strategy_input_bars_path=bars,
        output_dir=output_dir,
        bundle_dir=bundle_dir,
        acceptance_dir=acceptance_dir,
    )

    assert report.status == "pass"
    assert report.accepted is True
    assert report.ready_for_future_consumer_evidence_release is True
    assert report.adapter_request_count == 3
    assert outputs["readiness_json"].exists()
    assert outputs["bundle_json"].exists()
    assert outputs["acceptance_json"].exists()

    readiness = json.loads(outputs["readiness_json"].read_text(encoding="utf-8"))
    assert readiness["status"] == "pass"
    assert readiness["ready_for_future_consumer_evidence_release"] is True


def test_bridge_fails_when_contract_is_missing(tmp_path):
    report = build_dependency_bridge_report(
        strategy_input_contract_path=tmp_path / "missing_contract.json",
        strategy_input_bars_path=tmp_path / "missing_bars.jsonl",
        output_dir=tmp_path / "readiness",
        bundle_dir=tmp_path / "bundle",
        acceptance_dir=tmp_path / "acceptance",
    )

    assert report.status == "fail"
    assert report.accepted is False
    assert any(issue.code == "json_missing" for issue in report.issues)


def test_bridge_fails_when_contract_is_not_pass(tmp_path):
    contract = tmp_path / "strategy_input_contract.json"
    bars = tmp_path / "strategy_input_bars.jsonl"

    _write_json(
        contract,
        {
            "status": "fail",
            "input_event_count": 1,
            "accepted_bar_count": 1,
        },
    )
    _write_jsonl(
        bars,
        [{"bar_index": 1, "timestamp": "2026-01-01T09:15:00", "close": 100.0}],
    )

    report = build_dependency_bridge_report(
        strategy_input_contract_path=contract,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "readiness",
        bundle_dir=tmp_path / "bundle",
        acceptance_dir=tmp_path / "acceptance",
    )

    assert report.status == "fail"
    assert any(issue.code == "strategy_input_contract_not_pass" for issue in report.issues)


def test_bridge_rejects_execution_fields_in_bars(tmp_path):
    contract = tmp_path / "strategy_input_contract.json"
    bars = tmp_path / "strategy_input_bars.jsonl"

    _write_json(
        contract,
        {
            "status": "pass",
            "input_event_count": 1,
            "accepted_bar_count": 1,
        },
    )
    _write_jsonl(
        bars,
        [
            {
                "bar_index": 1,
                "timestamp": "2026-01-01T09:15:00",
                "close": 100.0,
                "order_id": "REAL-ORDER-NOT-ALLOWED",
            }
        ],
    )

    report = build_dependency_bridge_report(
        strategy_input_contract_path=contract,
        strategy_input_bars_path=bars,
        output_dir=tmp_path / "readiness",
        bundle_dir=tmp_path / "bundle",
        acceptance_dir=tmp_path / "acceptance",
    )

    assert report.status == "fail"
    assert any(
        issue.code == "strategy_input_bars_contain_execution_fields"
        for issue in report.issues
    )


def test_safety_notice_preserves_paper_only_language():
    notice = safety_notice().lower()

    assert "paper/simulation" in notice
    assert "does not" in notice
    assert "connect to brokers" in notice
    assert "place real orders" in notice
    assert "use real money" in notice
    assert "prove profitability" in notice
