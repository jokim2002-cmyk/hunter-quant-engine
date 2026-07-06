from __future__ import annotations

import importlib
import io
import json
import sys
from pathlib import Path


def test_run_paper_trading_demo_smoke() -> None:
    script_path = Path("examples/run_paper_trading_demo.py")
    assert script_path.exists()

    # Import locally so this test stays offline and does not spawn processes.
    demo = importlib.import_module("examples.run_paper_trading_demo")

    rc = demo.run_demo()
    assert rc == 0


def test_demo_output_and_safety_constraints() -> None:
    script_path = Path("examples/run_paper_trading_demo.py")
    demo = importlib.import_module("examples.run_paper_trading_demo")

    buf = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        rc = demo.run_demo()
    finally:
        sys.stdout = old_stdout

    out = buf.getvalue().lower()
    assert rc == 0

    # Short trader-readable demo messages.
    assert "fake/local paper trading demo" in out
    assert "synthetic option-buy trade plan" in out
    assert "paper trade symbol: nifty26jul24200ce" in out
    assert "paper trade quantity: 130" in out
    assert "paper entry premium: 100.0" in out
    assert "paper simulated exit premium: 135.0" in out
    assert "paper order id: paper-000001" in out
    assert "paper close status: closed" in out
    assert "paper exit id: paper-exit-000001" in out

    # Paper-only simulated P&L messages.
    assert "paper simulated points: 35.0" in out
    assert "paper simulated gross pnl: 4550.0" in out
    assert "paper estimated costs: 53.0" in out
    assert "paper simulated net pnl: 4497.0" in out
    assert "paper open positions: 0" in out
    assert "paper closed trades: 1" in out

    # Local report writer output stays concise in terminal.
    assert "paper report output dir:" in out
    assert "paper report text:" in out
    assert "paper report files are local/generated" in out
    assert "paper report summary json:" not in out
    assert "paper report orders json:" not in out
    assert "paper report open positions json:" not in out
    assert "paper report exit records json:" not in out

    # Removed noisy before/after position dump.
    assert "paper position symbol before close" not in out
    assert "paper position quantity before close" not in out
    assert "paper position after close" not in out
    assert "session summary total orders before close" not in out
    assert "session summary total orders after close" not in out

    # Safety / no broker / no live market data / no real orders.
    assert "paper pnl is simulation only" in out
    assert "estimated costs are included in net pnl only" in out
    assert "gross pnl excludes costs" in out
    assert "no broker/fyers" in out
    assert "no live/real market data" in out
    assert "no real orders placed" in out
    assert "not a profitability claim" in out

    # Forbidden SDK import check: safety text may mention FYERS, imports must not.
    source = script_path.read_text(encoding="utf-8").lower()
    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source

    assert "clean_paper_trading_report_bundle" in source

    # No broker order execution method names.
    forbidden_tokens = ["place" + "_order", "send" + "_order", "execute" + "_order"]
    for token in forbidden_tokens:
        assert token not in source


def test_demo_cleans_report_bundle_before_writing(monkeypatch) -> None:
    demo = importlib.import_module("examples.run_paper_trading_demo")
    from src.paper_trading.paper_trading_report_writer import (
        clean_paper_trading_report_bundle,
    )

    calls: list[Path] = []

    def spy_clean_report_bundle(output_dir: str | Path = Path("reports") / "paper_trading"):
        calls.append(Path(output_dir))
        return clean_paper_trading_report_bundle(output_dir)

    monkeypatch.setattr(
        demo,
        "clean_paper_trading_report_bundle",
        spy_clean_report_bundle,
    )

    rc = demo.run_demo()

    assert rc == 0
    assert calls == [Path("reports") / "paper_trading"]


def test_demo_writes_local_report_files_under_reports() -> None:
    demo = importlib.import_module("examples.run_paper_trading_demo")

    rc = demo.run_demo()

    assert rc == 0

    output_dir = Path("reports") / "paper_trading"
    expected_files = [
        output_dir / "manifest.json",
        output_dir / "summary.json",
        output_dir / "summary.csv",
        output_dir / "orders.json",
        output_dir / "orders.csv",
        output_dir / "open_positions.json",
        output_dir / "open_positions.csv",
        output_dir / "exit_records.json",
        output_dir / "exit_records.csv",
        output_dir / "report.txt",
    ]

    for path in expected_files:
        assert path.exists()
        assert "reports" in [part.lower() for part in path.parts]

    manifest_payload = json.loads(
        (output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    summary_payload = json.loads(
        (output_dir / "summary.json").read_text(encoding="utf-8")
    )
    exit_records_payload = json.loads(
        (output_dir / "exit_records.json").read_text(encoding="utf-8")
    )
    report_text = (output_dir / "report.txt").read_text(encoding="utf-8").lower()

    assert manifest_payload["report_version"] == 1
    assert manifest_payload["report_source"] == "paper"
    assert "generated_at" in manifest_payload
    assert manifest_payload["paper_pnl_is_simulation_only"] is True
    assert manifest_payload["files"]["manifest_json"].endswith("manifest.json")
    assert manifest_payload["files"]["summary_json"].endswith("summary.json")
    assert manifest_payload["files"]["report_text"].endswith("report.txt")

    assert summary_payload["report_version"] == 1
    assert summary_payload["report_source"] == "paper"
    assert "generated_at" in summary_payload
    assert summary_payload["total_orders"] == 1
    assert summary_payload["open_positions_count"] == 0
    assert summary_payload["total_open_quantity"] == 0
    assert summary_payload["symbols"] == []
    assert summary_payload["has_open_positions"] is False
    assert summary_payload["closed_trades_count"] == 1
    assert summary_payload["has_closed_trades"] is True
    assert summary_payload["exits_with_pnl_count"] == 1
    assert summary_payload["total_simulated_gross_pnl"] == 4550.0
    assert summary_payload["total_estimated_costs"] == 53.0
    assert summary_payload["total_simulated_net_pnl"] == 4497.0
    assert summary_payload["winning_exits_count"] == 1
    assert summary_payload["losing_exits_count"] == 0
    assert summary_payload["flat_exits_count"] == 0
    assert summary_payload["unknown_pnl_exits_count"] == 0
    assert summary_payload["net_winning_exits_count"] == 1
    assert summary_payload["net_losing_exits_count"] == 0
    assert summary_payload["net_flat_exits_count"] == 0
    assert summary_payload["unknown_net_pnl_exits_count"] == 0
    assert summary_payload["paper_pnl_is_simulation_only"] is True
    assert summary_payload["estimated_costs_included_in_net_pnl"] is True
    assert summary_payload["gross_pnl_excludes_costs"] is True

    assert len(exit_records_payload) == 1
    assert exit_records_payload[0]["exit_id"] == "PAPER-EXIT-000001"
    assert exit_records_payload[0]["symbol"] == "NIFTY26JUL24200CE"
    assert exit_records_payload[0]["simulated_points"] == 35.0
    assert exit_records_payload[0]["simulated_gross_pnl"] == 4550.0
    assert exit_records_payload[0]["estimated_exit_charges"] == 40.0
    assert exit_records_payload[0]["estimated_slippage"] == 13.0
    assert exit_records_payload[0]["total_estimated_costs"] == 53.0
    assert exit_records_payload[0]["simulated_net_pnl"] == 4497.0

    assert "paper trading p&l summary" in report_text
    assert "closed trades count: 1" in report_text
    assert "total simulated gross pnl: 4550.0" in report_text
    assert "total estimated costs: 53.0" in report_text
    assert "total simulated net pnl: 4497.0" in report_text
    assert "winning exits count: 1" in report_text
    assert "net winning exits count: 1" in report_text
    assert "paper pnl is simulation only" in report_text
    assert "estimated costs are included in net pnl only" in report_text
    assert "gross pnl excludes costs" in report_text
    assert "not a profitability claim" in report_text
