from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
MODULE = SCRIPTS / "hqe_trader_report_renderer.py"
APP = SCRIPTS / "hqe_product_app_v2.py"


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "hqe_trader_report_renderer",
        MODULE,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_day_one_payload():
    return {
        "action": "NOT_AVAILABLE",
        "auto_trading_allowed": False,
        "broker_execution_allowed": False,
        "created_at": "2026-07-10T15:39:02",
        "day_label": "DAY_001_2026-07-10",
        "day_status": "NO_COMPLETED_TRADES_HOLD_MORE_DATA_REQUIRED",
        "entry": "",
        "event": "",
        "evidence_counts": {
            "ledger_rows": 0,
            "overlay_audit_rows": 0,
            "overlay_report_present": False,
            "reason_log_rows": 0,
            "supervisor_report_present": False,
        },
        "exit_reason": "",
        "gate": "NOT_AVAILABLE",
        "ledger_evaluator_status": "",
        "ledger_stats": {
            "average_closed_trade_paper_pnl": 0.0,
            "closed_positions": 0,
            "flats": 0,
            "losses": 0,
            "open_positions_estimated": 0,
            "opened_positions": 0,
            "total_paper_pnl": 0,
            "wins": 0,
        },
        "locked_candidate": (
            "ER20_GE_030_PE_ONLY_DTE_GE_1_"
            "LTP_20_200_SL040_TGT120"
        ),
        "module": 133,
        "module_name": "Daily Paper Trading Report Pack",
        "operator_message": "",
        "option_selling_allowed": False,
        "paper_only": True,
        "paper_pnl": "0.0",
        "pe_reason": "NOT_AVAILABLE",
        "plain_hinglish_reason": "",
        "position_state": "UNKNOWN",
        "profitability_claim": False,
        "real_money_allowed": False,
        "real_orders_allowed": False,
        "signal_generated": False,
        "source_files": {
            "overlay_audit_csv": "",
            "overlay_json": "",
            "overlay_report": "",
            "paper_ledger": "DAY_001_FORWARD_TRADE_LOG.csv",
            "reason_log": "",
            "supervisor_report": "",
            "supervisor_summary": "",
        },
        "stop_loss": "",
        "target": "",
    }


def test_exact_day_one_report_is_simple_and_correct(tmp_path, monkeypatch):
    module = load_module()
    source = tmp_path / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
    source.write_text(
        json.dumps(exact_day_one_payload()),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "resolve_latest_report", lambda _: source)
    monkeypatch.setattr(module, "resolve_latest_evidence", lambda _: source)

    result = module.ensure_trader_report(tmp_path)
    assert result is not None and result.exists()

    report_html = result.read_text(encoding="utf-8")
    assert "NO PAPER TRADE TODAY" in report_html
    assert "Day 001" in report_html
    assert "10 Jul 2026" in report_html
    assert "Not generated" in report_html
    assert "No position" in report_html
    assert "₹0.00" in report_html
    assert "No signal + no entry + no completed trade" in report_html
    assert "PE only" in report_html
    assert "₹20 to ₹200" in report_html
    assert "Paper ledger me koi trade row record nahi hui." in report_html

    assert "ER20_GE_030_PE_ONLY" not in report_html.split(
        '<section class="metrics">'
    )[0]
    assert report_html.count("Raw daily report JSON") == 1
    assert "Raw market-close evidence JSON" not in report_html


def test_renderer_returns_none_without_json_source(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "resolve_latest_report", lambda _: None)
    monkeypatch.setattr(module, "resolve_latest_evidence", lambda _: None)
    assert module.ensure_trader_report(tmp_path) is None


def test_app_still_opens_trader_html_and_separates_json():
    text = APP.read_text(encoding="utf-8-sig")
    assert "report = ensure_trader_report(workspace)" in text
    assert 'text="Open Trader Report"' in text
    assert 'text="Open Technical Evidence (JSON)"' in text
