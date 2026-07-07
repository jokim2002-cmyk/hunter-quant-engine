"""
Paper Trading Journal Index CLI Tests

Fake/local replay journal run listing only. No real orders. No broker code.
"""

import json
from pathlib import Path

from src.paper_trading.paper_trading_journal_index_cli import (
    format_paper_trading_journal_index,
    main,
    run_index_view,
)


def test_format_paper_trading_journal_index_handles_empty_index():
    text = format_paper_trading_journal_index(
        {
            "journal_source": "paper",
            "runs": [],
        }
    )

    assert "Hunter Quant Engine - Paper Replay Journal Runs" in text
    assert "fake/local paper replay only" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text
    assert "paper pnl is simulation only" in text
    assert "runs count: 0" in text
    assert "No replay journal runs found." in text
    assert "Run hqe_paper_replay_journal.bat first." in text


def test_format_paper_trading_journal_index_lists_runs():
    text = format_paper_trading_journal_index(
        {
            "journal_source": "paper",
            "runs": [
                {
                    "run_id": "demo-replay-journal",
                    "generated_at": "2026-07-06T09:30:00+00:00",
                    "output_dir": "reports/paper_trading/journal/demo-replay-journal",
                    "summary_json": "reports/paper_trading/journal/demo-replay-journal/summary.json",
                    "manifest_json": "reports/paper_trading/journal/demo-replay-journal/manifest.json",
                }
            ],
        }
    )

    assert "runs count: 1" in text
    assert "1. run id: demo-replay-journal" in text
    assert "generated at: 2026-07-06T09:30:00+00:00" in text
    assert "summary json: reports/paper_trading/journal/demo-replay-journal/summary.json" in text
    assert "manifest json: reports/paper_trading/journal/demo-replay-journal/manifest.json" in text


def test_journal_index_cli_main_handles_missing_index(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 0

    out = capsys.readouterr().out

    assert "Hunter Quant Engine - Paper Replay Journal Runs" in out
    assert "runs count: 0" in out
    assert "No replay journal runs found." in out


def test_journal_index_cli_prints_existing_index(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    index_dir = tmp_path / "reports" / "paper_trading" / "journal"
    index_dir.mkdir(parents=True)
    (index_dir / "index.json").write_text(
        json.dumps(
            {
                "journal_index_version": 1,
                "journal_source": "paper",
                "paper_journal_is_local_only": True,
                "paper_pnl_is_simulation_only": True,
                "runs": [
                    {
                        "run_id": "run-001",
                        "generated_at": "2026-07-06T09:30:00+00:00",
                        "output_dir": "reports/paper_trading/journal/run-001",
                        "summary_json": "reports/paper_trading/journal/run-001/summary.json",
                        "manifest_json": "reports/paper_trading/journal/run-001/manifest.json",
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert run_index_view() == 0

    out = capsys.readouterr().out

    assert "runs count: 1" in out
    assert "run id: run-001" in out
    assert "summary json: reports/paper_trading/journal/run-001/summary.json" in out


def test_paper_replay_journal_runs_shortcut_points_to_safe_cli():
    text = Path("hqe_paper_replay_journal_runs.bat").read_text(
        encoding="utf-8"
    ).lower()

    assert "src.paper_trading.paper_trading_journal_index_cli" in text
    assert ".venv\\scripts\\python.exe" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text


def test_journal_index_cli_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_trading_journal_index_cli.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source

