"""
Paper Trading Replay Journal Demo CLI Tests

Fake/local replay journal demo only. No real orders. No broker code.
"""

import json
import subprocess
import sys
from pathlib import Path

from src.paper_trading.paper_trading_replay_journal_demo_cli import (
    DEMO_RUN_ID,
    main,
    run_demo,
)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_replay_journal_demo_main_returns_zero_and_prints_safety_lines(
    capsys,
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    assert main() == 0

    out = capsys.readouterr().out

    assert "Hunter Quant Engine - Paper Replay Journal Demo" in out
    assert "fake/local paper replay only" in out
    assert "no broker" in out
    assert "no live market data" in out
    assert "no real orders" in out
    assert "not a profitability claim" in out
    assert "paper replay journal files are local/generated" in out
    assert "paper pnl is simulation only" in out


def test_replay_journal_demo_writes_expected_journal_files(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert run_demo() == 0

    output_dir = (
        tmp_path
        / "reports"
        / "paper_trading"
        / "journal"
        / DEMO_RUN_ID
    )

    expected_files = (
        "metadata.json",
        "summary.json",
        "orders.json",
        "open_positions.json",
        "exit_records.json",
        "manifest.json",
    )

    for filename in expected_files:
        path = output_dir / filename
        assert path.exists()
        assert "reports" in [part.lower() for part in path.parts]


def test_replay_journal_demo_summary_contains_simulated_net_pnl(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert run_demo() == 0

    summary_path = (
        tmp_path
        / "reports"
        / "paper_trading"
        / "journal"
        / DEMO_RUN_ID
        / "summary.json"
    )
    summary = _read_json(summary_path)

    assert summary["run_id"] == DEMO_RUN_ID
    assert summary["total_orders"] == 1
    assert summary["closed_trades_count"] == 1
    assert summary["total_simulated_gross_pnl"] == 2275.0
    assert summary["total_estimated_costs"] == 50.0
    assert summary["total_simulated_net_pnl"] == 2225.0
    assert summary["paper_pnl_is_simulation_only"] is True


def test_paper_replay_journal_shortcut_points_to_safe_demo_module():
    text = Path("hqe_paper_replay_journal.bat").read_text(encoding="utf-8").lower()

    assert "src.paper_trading.paper_trading_replay_journal_demo_cli" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_replay_journal_demo_cli_source_has_no_external_order_execution_imports():
    source = Path(
        "src/paper_trading/paper_trading_replay_journal_demo_cli.py"
    ).read_text(encoding="utf-8").lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def test_replay_journal_demo_cleans_known_generated_files_before_writing(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)

    output_dir = (
        tmp_path
        / "reports"
        / "paper_trading"
        / "journal"
        / DEMO_RUN_ID
    )
    output_dir.mkdir(parents=True)

    stale_manifest = output_dir / "manifest.json"
    stale_manifest.write_text("stale", encoding="utf-8")

    unknown_file = output_dir / "manual-note.txt"
    unknown_file.write_text("keep", encoding="utf-8")

    assert run_demo() == 0

    assert stale_manifest.read_text(encoding="utf-8") != "stale"
    assert unknown_file.read_text(encoding="utf-8") == "keep"
