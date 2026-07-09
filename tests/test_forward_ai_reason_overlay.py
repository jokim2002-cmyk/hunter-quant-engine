import csv
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_ai_reason_overlay.py"
SPEC = importlib.util.spec_from_file_location("build_forward_ai_reason_overlay", SCRIPT_PATH)
overlay_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = overlay_module
SPEC.loader.exec_module(overlay_module)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_reason_log(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def test_safety_contract_is_paper_only():
    assert overlay_module.PAPER_ONLY is True
    assert overlay_module.EXTERNAL_AI_API_ALLOWED is False
    assert overlay_module.BROKER_EXECUTION_ALLOWED is False
    assert overlay_module.REAL_ORDERS_ALLOWED is False
    assert overlay_module.REAL_MONEY_ALLOWED is False
    assert overlay_module.AUTO_TRADING_ALLOWED is False
    assert overlay_module.OPTION_SELLING_ALLOWED is False
    overlay_module.assert_safety_contract()


def test_overlay_accepts_pe_buy_signal(tmp_path):
    summary_path = tmp_path / "summary.json"
    reason_log = tmp_path / "reason.csv"
    state_json = tmp_path / "state.json"

    write_json(
        summary_path,
        {
            "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
            "data_ready": True,
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING; DTE_OK(2); LTP_OK(100.00)",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "paper_pnl": 0.0,
            "position_state": "OPEN",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        },
    )
    write_reason_log(
        reason_log,
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
        },
    )
    write_json(state_json, {"status": "OPEN", "entry": 100.0, "stop_loss": 60.0, "target": 220.0})

    inputs = overlay_module.OverlayInputs(summary_path, reason_log, state_json, tmp_path / "out")
    overlay = overlay_module.build_overlay(inputs)

    assert overlay["action"] == "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY"
    assert overlay["gate"] == "HOLD_MORE_DATA_REQUIRED"
    assert overlay["paper_only"] is True
    assert overlay["broker_execution_allowed"] is False
    assert overlay["real_orders_allowed"] is False
    assert "Entry 100.0" in overlay["plain_hinglish_reason"]


def test_overlay_waits_when_data_not_ready(tmp_path):
    summary_path = tmp_path / "summary.json"
    write_json(
        summary_path,
        {
            "data_ready": False,
            "signal_generated": False,
            "event": "NO_SIGNAL",
            "pe_reason": "PREMIUM_DATA_NOT_READY",
            "position_state": "FLAT",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        },
    )

    inputs = overlay_module.OverlayInputs(summary_path, None, None, tmp_path / "out")
    overlay = overlay_module.build_overlay(inputs)

    assert overlay["action"] == "WAIT_DATA_NOT_READY_PAPER_ONLY"
    assert "Data abhi ready nahi hai" in overlay["plain_hinglish_reason"]
    assert overlay["auto_trading_allowed"] is False


def test_overlay_closes_position_with_pnl_review(tmp_path):
    summary_path = tmp_path / "summary.json"
    write_json(
        summary_path,
        {
            "data_ready": True,
            "signal_generated": False,
            "event": "POSITION_CLOSED",
            "pe_reason": "Position exit rule triggered",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "exit_reason": "TARGET_HIT_PAPER_ONLY",
            "paper_pnl": 120.0,
            "position_state": "FLAT",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_1_OF_30",
        },
    )

    inputs = overlay_module.OverlayInputs(summary_path, None, None, tmp_path / "out")
    overlay = overlay_module.build_overlay(inputs)

    assert overlay["action"] == "POSITION_CLOSED_PAPER_ONLY_REVIEW_PNL"
    assert overlay["paper_pnl"] == 120.0
    assert "Profitability claim" not in overlay["operator_message"]


def test_overlay_writes_report_json_and_audit_csv(tmp_path):
    overlay = {
        "module": 132,
        "module_name": "Forward AI Reason Overlay",
        "created_at": "2026-07-09T11:00:00",
        "paper_only": True,
        "external_ai_api_allowed": False,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "profitability_claim": False,
        "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
        "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
        "gate": "HOLD_MORE_DATA_REQUIRED",
        "signal_generated": True,
        "event": "POSITION_OPENED",
        "pe_reason": "ER20_OK",
        "entry": 100.0,
        "stop_loss": 60.0,
        "target": 220.0,
        "exit_reason": "",
        "paper_pnl": 0.0,
        "position_state": "OPEN",
        "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        "plain_hinglish_reason": "Locked candidate ne PE buy paper signal accept kiya hai.",
        "operator_message": "Paper PE signal logged. Position simulated only. Real order mat lagana.",
        "source_files": {},
    }

    files = overlay_module.write_overlay_files(tmp_path / "out", overlay)

    assert Path(files["overlay_json"]).exists()
    assert Path(files["overlay_report"]).exists()
    assert Path(files["audit_csv"]).exists()
    assert "External AI/API call: NO" in Path(files["overlay_report"]).read_text(encoding="utf-8")
