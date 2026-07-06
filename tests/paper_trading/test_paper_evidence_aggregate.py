"""Tests for paper evidence aggregate runner."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.paper_trading.paper_evidence_aggregate import (
    PaperEvidenceAggregateThresholds,
    build_paper_evidence_aggregate_report,
    format_paper_evidence_aggregate_report,
    load_paper_evidence_json,
    main,
    paper_evidence_aggregate_report_to_dict,
    run_paper_evidence_aggregate,
)


_GENERATED_AT = datetime(2026, 7, 6, 9, 15)


def _evidence(
    *,
    passed: bool = True,
    total_orders: int = 1,
    open_positions: int = 0,
    closed_trades: int = 1,
    exit_records: int = 1,
    unknown_trades: int = 0,
    simulated_gross_pnl: float = 4550.0,
    estimated_costs: float = 15.0,
    simulated_net_pnl: float = 4535.0,
):
    return {
        "passed": passed,
        "paper_evidence_is_simulation_only": True,
        "no_broker_orders": True,
        "no_live_market_data": True,
        "no_real_orders": True,
        "not_a_profitability_claim": True,
        "total_orders": total_orders,
        "open_positions": open_positions,
        "closed_trades": closed_trades,
        "exit_records": exit_records,
        "unknown_trades": unknown_trades,
        "simulated_gross_pnl": simulated_gross_pnl,
        "estimated_costs": estimated_costs,
        "simulated_net_pnl": simulated_net_pnl,
    }


def test_load_paper_evidence_json_reads_object(tmp_path):
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")

    payload = load_paper_evidence_json(evidence_path)

    assert payload["passed"] is True
    assert payload["closed_trades"] == 1


def test_paper_evidence_aggregate_passes_with_good_evidence():
    report = build_paper_evidence_aggregate_report(
        [_evidence()],
        source_paths=["reports/paper_trading/operator_demo/evidence/evidence.json"],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is True
    assert report.report_count == 1
    assert report.all_reports_passed is True
    assert report.total_closed_trades == 1
    assert report.total_simulated_net_pnl == 4535.0
    assert report.blocking_reasons == ()


def test_paper_evidence_aggregate_blocks_empty_input():
    report = build_paper_evidence_aggregate_report(
        [],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is False
    assert "evidence reports below minimum: 0 < 1" in report.blocking_reasons
    assert "closed trades below minimum: 0 < 1" in report.blocking_reasons


def test_paper_evidence_aggregate_blocks_failed_child_report():
    report = build_paper_evidence_aggregate_report(
        [_evidence(passed=False)],
        generated_at=_GENERATED_AT,
    )

    assert report.passed is False
    assert "one or more evidence reports failed their gates" in report.blocking_reasons


def test_paper_evidence_aggregate_blocks_custom_net_pnl_threshold():
    report = build_paper_evidence_aggregate_report(
        [_evidence(simulated_net_pnl=100.0)],
        thresholds=PaperEvidenceAggregateThresholds(
            min_total_simulated_net_pnl=500.0,
        ),
        generated_at=_GENERATED_AT,
    )

    assert report.passed is False
    assert "simulated net pnl below minimum: 100.0 < 500.0" in report.blocking_reasons


def test_paper_evidence_aggregate_writes_outputs_under_reports(tmp_path):
    evidence_path = tmp_path / "reports" / "paper_trading" / "operator_demo" / "evidence" / "evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")

    report, paths = run_paper_evidence_aggregate(
        [evidence_path],
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence_aggregate",
        generated_at=_GENERATED_AT,
    )

    assert report.passed is True
    assert paths.aggregate_json.exists()
    assert paths.aggregate_text.exists()
    assert paths.manifest_json.exists()

    text = paths.aggregate_text.read_text(encoding="utf-8")
    assert "Hunter Quant Engine - Paper Evidence Aggregate" in text
    assert "not a profitability claim" in text
    assert "passed gates: True" in text


def test_paper_evidence_aggregate_report_dict_is_json_safe():
    report = build_paper_evidence_aggregate_report(
        [_evidence()],
        source_paths=["reports/paper_trading/operator_demo/evidence/evidence.json"],
        generated_at=_GENERATED_AT,
    )

    payload = paper_evidence_aggregate_report_to_dict(report)

    assert payload["paper_evidence_is_simulation_only"] is True
    assert payload["source_files"] == [
        "reports/paper_trading/operator_demo/evidence/evidence.json"
    ]
    assert payload["blocking_reasons"] == []


def test_paper_evidence_aggregate_rejects_output_outside_reports(tmp_path):
    evidence_path = tmp_path / "reports" / "paper_trading" / "operator_demo" / "evidence" / "evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")

    with pytest.raises(ValueError, match="reports/"):
        run_paper_evidence_aggregate(
            [evidence_path],
            output_dir=tmp_path / "evidence_aggregate",
        )


def test_paper_evidence_aggregate_main_handles_missing_default(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 1

    out = capsys.readouterr().out

    assert "ERROR: paper evidence JSON not found" in out
    assert "Run hqe_paper_mvp_operator_demo.bat first." in out


def test_format_paper_evidence_aggregate_report_is_trader_friendly():
    report = build_paper_evidence_aggregate_report(
        [_evidence()],
        generated_at=_GENERATED_AT,
    )

    text = format_paper_evidence_aggregate_report(report)

    assert "Hunter Quant Engine - Paper Evidence Aggregate" in text
    assert "paper/simulation only" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text
    assert "report count: 1" in text
    assert "net pnl: 4535.0" in text


def test_paper_evidence_aggregate_shortcut_points_to_safe_cli():
    text = Path("hqe_paper_evidence_aggregate.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.paper_evidence_aggregate" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_paper_evidence_aggregate_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_evidence_aggregate.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
