"""
Paper Trading Replay Journal Summary CLI Tests

Fake/local replay journal summary only. No real orders. No broker code.
"""

import json
from pathlib import Path

from src.paper_trading.paper_trading_replay_journal_summary_cli import (
    format_replay_journal_summary,
    load_replay_journal_summary,
    main,
    run_summary_view,
)


def test_load_replay_journal_summary_reads_json(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps({"session_id": "demo-session", "total_orders": 1}),
        encoding="utf-8",
    )

    payload = load_replay_journal_summary(summary_path)

    assert payload == {"session_id": "demo-session", "total_orders": 1}


def test_format_replay_journal_summary_prints_trader_friendly_lines():
    text = format_replay_journal_summary(
        {
            "session_id": "demo-session",
            "started_at": "2026-07-06T09:30:00+00:00",
            "total_orders": 2,
            "accepted_orders": 2,
            "rejected_orders": 0,
            "open_positions": 1,
            "closed_trades": 1,
            "exit_records": 1,
            "total_simulated_gross_pnl": 100.0,
            "total_estimated_costs": 12.5,
            "total_simulated_net_pnl": 87.5,
            "net_winning_trades": 1,
            "net_losing_trades": 0,
            "net_flat_trades": 0,
            "net_unknown_trades": 0,
        }
    )

    assert "Hunter Quant Engine - Paper Replay Journal Summary" in text
    assert "fake/local paper replay only" in text
    assert "no broker" in text
    assert "no live market data" in text
    assert "no real orders" in text
    assert "not a profitability claim" in text
    assert "paper pnl is simulation only" in text
    assert "session id: demo-session" in text
    assert "total orders: 2" in text
    assert "open positions: 1" in text
    assert "closed trades: 1" in text
    assert "gross pnl: 100.0" in text
    assert "estimated costs: 12.5" in text
    assert "net pnl: 87.5" in text
    assert "wins: 1" in text


def test_run_summary_view_prints_existing_summary(capsys, tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "session_id": "demo-session",
                "total_orders": 1,
                "accepted_orders": 1,
                "rejected_orders": 0,
            }
        ),
        encoding="utf-8",
    )

    assert run_summary_view(summary_path) == 0

    out = capsys.readouterr().out

    assert "Paper Replay Journal Summary" in out
    assert "session id: demo-session" in out
    assert "total orders: 1" in out


def test_run_summary_view_returns_one_when_summary_is_missing(capsys, tmp_path):
    missing_path = tmp_path / "missing-summary.json"

    assert run_summary_view(missing_path) == 1

    out = capsys.readouterr().out

    assert "ERROR: paper replay journal summary not found" in out
    assert "Run hqe_paper_replay_journal.bat first." in out


def test_summary_cli_main_handles_missing_default_summary(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert main() == 1

    out = capsys.readouterr().out

    assert "ERROR: paper replay journal summary not found" in out
    assert "Run hqe_paper_replay_journal.bat first." in out


def test_summary_cli_source_has_no_external_order_execution_imports():
    source = Path(
        "src/paper_trading/paper_trading_replay_journal_summary_cli.py"
    ).read_text(encoding="utf-8").lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source
