import csv
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_daily_paper_trading_report_pack.py"
SPEC = importlib.util.spec_from_file_location("build_daily_paper_trading_report_pack", SCRIPT_PATH)
pack_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pack_module
SPEC.loader.exec_module(pack_module)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_inputs(tmp_path: Path) -> pack_module.ReportPackInputs:
    supervisor_summary = tmp_path / "MODULE_131_SUPERVISOR_SUMMARY.json"
    supervisor_report = tmp_path / "MODULE_131_INTRADAY_SUPERVISOR_REPORT.md"
    reason_log = tmp_path / "MODULE_131_SIGNAL_REASON_LOG.csv"
    paper_ledger = tmp_path / "MODULE_131_PAPER_LEDGER.csv"
    overlay_json = tmp_path / "MODULE_132_AI_REASON_OVERLAY.json"
    overlay_report = tmp_path / "MODULE_132_AI_REASON_OVERLAY_REPORT.md"
    overlay_audit_csv = tmp_path / "MODULE_132_DECISION_AUDIT.csv"

    write_json(
        supervisor_summary,
        {
            "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
            "data_ready": True,
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING; DTE_OK(2); LTP_OK(100.00)",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "exit_reason": "",
            "paper_pnl": 0.0,
            "position_state": "OPEN",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        },
    )
    supervisor_report.write_text("# Supervisor report\n", encoding="utf-8")

    write_csv(
        reason_log,
        [
            "timestamp",
            "module",
            "data_ready",
            "readiness_reason",
            "signal_generated",
            "event",
            "pe_reason",
            "entry",
            "stop_loss",
            "target",
            "exit_reason",
            "paper_pnl",
            "position_state",
        ],
        [
            {
                "timestamp": "2026-07-09T10:55:00",
                "module": "131",
                "data_ready": "YES",
                "readiness_reason": "DATA_READY",
                "signal_generated": "YES",
                "event": "POSITION_OPENED",
                "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING",
                "entry": "100.0",
                "stop_loss": "60.0",
                "target": "220.0",
                "exit_reason": "",
                "paper_pnl": "0.0",
                "position_state": "OPEN",
            }
        ],
    )

    write_csv(
        paper_ledger,
        [
            "timestamp",
            "module",
            "event",
            "side",
            "entry",
            "stop_loss",
            "target",
            "exit_reason",
            "paper_pnl",
            "paper_only",
        ],
        [
            {
                "timestamp": "2026-07-09T10:55:00",
                "module": "131",
                "event": "POSITION_OPENED",
                "side": "PE_BUY",
                "entry": "100.0",
                "stop_loss": "60.0",
                "target": "220.0",
                "exit_reason": "",
                "paper_pnl": "0.0",
                "paper_only": "True",
            }
        ],
    )

    write_json(
        overlay_json,
        {
            "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
            "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
            "gate": "HOLD_MORE_DATA_REQUIRED",
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING; DTE_OK(2); LTP_OK(100.00)",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "exit_reason": "",
            "paper_pnl": 0.0,
            "position_state": "OPEN",
            "plain_hinglish_reason": "Locked candidate ne PE buy paper signal accept kiya hai.",
            "operator_message": "Paper PE signal logged. Position simulated only. Real order mat lagana.",
        },
    )
    overlay_report.write_text("# Overlay report\n", encoding="utf-8")

    write_csv(
        overlay_audit_csv,
        ["created_at", "module", "action", "gate", "signal_generated", "event"],
        [
            {
                "created_at": "2026-07-09T10:56:00",
                "module": "132",
                "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
                "gate": "HOLD_MORE_DATA_REQUIRED",
                "signal_generated": "True",
                "event": "POSITION_OPENED",
            }
        ],
    )

    return pack_module.ReportPackInputs(
        day_label="DAY_001",
        supervisor_summary=supervisor_summary,
        supervisor_report=supervisor_report,
        reason_log=reason_log,
        paper_ledger=paper_ledger,
        overlay_json=overlay_json,
        overlay_report=overlay_report,
        overlay_audit_csv=overlay_audit_csv,
        out_dir=tmp_path / "out",
    )


def test_safety_contract_is_paper_only():
    assert pack_module.PAPER_ONLY is True
    assert pack_module.BROKER_EXECUTION_ALLOWED is False
    assert pack_module.REAL_ORDERS_ALLOWED is False
    assert pack_module.REAL_MONEY_ALLOWED is False
    assert pack_module.AUTO_TRADING_ALLOWED is False
    assert pack_module.OPTION_SELLING_ALLOWED is False
    assert pack_module.PROFITABILITY_CLAIM is False
    pack_module.assert_safety_contract()


def test_aggregate_ledger_counts_closed_pnl():
    rows = [
        {"event": "POSITION_OPENED", "paper_pnl": "0"},
        {"event": "POSITION_CLOSED", "paper_pnl": "120"},
        {"event": "POSITION_OPENED", "paper_pnl": "0"},
        {"event": "POSITION_CLOSED", "paper_pnl": "-40"},
    ]
    stats = pack_module.aggregate_ledger(rows)
    assert stats["opened_positions"] == 2
    assert stats["closed_positions"] == 2
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert stats["total_paper_pnl"] == 80.0
    assert stats["average_closed_trade_paper_pnl"] == 40.0


def test_daily_pack_builds_from_module_131_and_132_outputs(tmp_path):
    inputs = make_inputs(tmp_path)
    pack = pack_module.build_daily_pack(inputs)

    assert pack["module"] == 133
    assert pack["paper_only"] is True
    assert pack["broker_execution_allowed"] is False
    assert pack["real_orders_allowed"] is False
    assert pack["auto_trading_allowed"] is False
    assert pack["day_label"] == "DAY_001"
    assert pack["signal_generated"] is True
    assert pack["action"] == "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY"
    assert pack["day_status"] == "HOLD_MORE_DATA_REQUIRED"
    assert pack["ledger_stats"]["opened_positions"] == 1
    assert pack["ledger_stats"]["closed_positions"] == 0
    assert pack["evidence_counts"]["supervisor_report_present"] is True
    assert pack["evidence_counts"]["overlay_report_present"] is True


def test_write_daily_pack_creates_report_csv_manifest_and_handover(tmp_path):
    inputs = make_inputs(tmp_path)
    pack = pack_module.build_daily_pack(inputs)
    files = pack_module.write_daily_pack(tmp_path / "out", pack)

    assert Path(files["daily_pack_json"]).exists()
    assert Path(files["daily_report_md"]).exists()
    assert Path(files["daily_summary_csv"]).exists()
    assert Path(files["evidence_manifest_csv"]).exists()
    assert Path(files["next_dry_run_handover"]).exists()

    report_text = Path(files["daily_report_md"]).read_text(encoding="utf-8")
    assert "Paper/simulation only: YES" in report_text
    assert "Broker execution: NO" in report_text
    assert "Real orders: NO" in report_text
    assert "Auto trading: NO" in report_text
    assert "not a profitability claim" in report_text.lower()


def test_day_status_no_trade_when_no_ledger_rows(tmp_path):
    inputs = make_inputs(tmp_path)
    inputs.paper_ledger.write_text("timestamp,module,event,paper_pnl\n", encoding="utf-8")
    pack = pack_module.build_daily_pack(inputs)
    assert pack["day_status"] == "NO_COMPLETED_TRADES_HOLD_MORE_DATA_REQUIRED"
