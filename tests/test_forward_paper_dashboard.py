import csv
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_paper_dashboard.py"
SPEC = importlib.util.spec_from_file_location("build_forward_paper_dashboard", SCRIPT_PATH)
dashboard_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = dashboard_module
SPEC.loader.exec_module(dashboard_module)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_inputs(tmp_path: Path) -> dashboard_module.DashboardInputs:
    daily_pack = tmp_path / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
    daily_summary = tmp_path / "MODULE_133_DAILY_SUMMARY.csv"
    manifest = tmp_path / "MODULE_133_EVIDENCE_MANIFEST.csv"
    supervisor = tmp_path / "MODULE_131_SUPERVISOR_SUMMARY.json"
    overlay = tmp_path / "MODULE_132_AI_REASON_OVERLAY.json"

    write_json(
        daily_pack,
        {
            "day_label": "DRY_RUN_001",
            "day_status": "HOLD_MORE_DATA_REQUIRED",
            "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
            "gate": "HOLD_MORE_DATA_REQUIRED",
            "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING; DTE_OK(2); LTP_OK(100.00)",
            "entry": 100.0,
            "stop_loss": 60.0,
            "target": 220.0,
            "exit_reason": "",
            "paper_pnl": 0.0,
            "position_state": "OPEN",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
            "plain_hinglish_reason": "Locked candidate ne PE buy paper signal accept kiya hai.",
            "operator_message": "Paper PE signal logged. Position simulated only. Real order mat lagana.",
            "ledger_stats": {
                "opened_positions": 1,
                "closed_positions": 0,
                "open_positions_estimated": 1,
                "wins": 0,
                "losses": 0,
                "flats": 0,
                "total_paper_pnl": 0.0,
                "average_closed_trade_paper_pnl": 0.0,
            },
            "evidence_counts": {
                "reason_log_rows": 1,
                "ledger_rows": 1,
                "overlay_audit_rows": 1,
            },
        },
    )

    write_csv(
        daily_summary,
        [
            "created_at",
            "day_label",
            "day_status",
            "locked_candidate",
            "signal_generated",
            "event",
            "action",
            "gate",
            "position_state",
            "entry",
            "stop_loss",
            "target",
            "exit_reason",
            "paper_pnl",
            "ledger_evaluator_status",
        ],
        [
            {
                "created_at": "2026-07-09T10:55:00",
                "day_label": "DRY_RUN_001",
                "day_status": "HOLD_MORE_DATA_REQUIRED",
                "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
                "signal_generated": "True",
                "event": "POSITION_OPENED",
                "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
                "gate": "HOLD_MORE_DATA_REQUIRED",
                "position_state": "OPEN",
                "entry": "100.0",
                "stop_loss": "60.0",
                "target": "220.0",
                "exit_reason": "",
                "paper_pnl": "0.0",
                "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
            }
        ],
    )

    write_csv(
        manifest,
        ["artifact", "path", "present"],
        [
            {"artifact": "daily_pack_json", "path": str(daily_pack), "present": "True"},
            {"artifact": "daily_summary_csv", "path": str(daily_summary), "present": "True"},
        ],
    )

    write_json(
        supervisor,
        {
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "position_state": "OPEN",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        },
    )

    write_json(
        overlay,
        {
            "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
            "gate": "HOLD_MORE_DATA_REQUIRED",
            "operator_message": "Paper PE signal logged. Position simulated only. Real order mat lagana.",
        },
    )

    return dashboard_module.DashboardInputs(
        day_label="DRY_RUN_001",
        daily_pack_json=daily_pack,
        daily_summary_csv=daily_summary,
        evidence_manifest_csv=manifest,
        supervisor_summary_json=supervisor,
        overlay_json=overlay,
        out_dir=tmp_path / "out",
    )


def test_safety_contract_is_read_only_paper_dashboard():
    assert dashboard_module.PAPER_ONLY is True
    assert dashboard_module.READ_ONLY_DASHBOARD is True
    assert dashboard_module.LOCAL_STATIC_HTML_ONLY is True
    assert dashboard_module.BROKER_EXECUTION_ALLOWED is False
    assert dashboard_module.REAL_ORDERS_ALLOWED is False
    assert dashboard_module.REAL_MONEY_ALLOWED is False
    assert dashboard_module.AUTO_TRADING_ALLOWED is False
    assert dashboard_module.OPTION_SELLING_ALLOWED is False
    assert dashboard_module.EXTERNAL_API_ALLOWED is False
    assert dashboard_module.PROFITABILITY_CLAIM is False
    dashboard_module.assert_safety_contract()


def test_build_dashboard_model_from_daily_pack(tmp_path):
    inputs = make_inputs(tmp_path)
    model = dashboard_module.build_dashboard_model(inputs)

    assert model["module"] == 134
    assert model["paper_only"] is True
    assert model["read_only_dashboard"] is True
    assert model["local_static_html_only"] is True
    assert model["broker_execution_allowed"] is False
    assert model["real_orders_allowed"] is False
    assert model["auto_trading_allowed"] is False
    assert model["dashboard_status"] == "HOLD_MORE_DATA_REQUIRED"
    assert model["signal_generated"] is True
    assert model["event"] == "POSITION_OPENED"
    assert model["ledger_stats"]["opened_positions"] == 1
    assert model["evidence_counts"]["manifest_rows"] == 2


def test_missing_inputs_create_no_data_dashboard_model(tmp_path):
    inputs = dashboard_module.DashboardInputs(
        day_label="EMPTY_DAY",
        daily_pack_json=None,
        daily_summary_csv=None,
        evidence_manifest_csv=None,
        supervisor_summary_json=None,
        overlay_json=None,
        out_dir=tmp_path / "out",
    )

    model = dashboard_module.build_dashboard_model(inputs)

    assert model["dashboard_status"] == "NO_DATA_LOADED"
    assert model["signal_generated"] is False
    assert model["position_state"] == "UNKNOWN"
    assert model["paper_only"] is True


def test_write_dashboard_files_creates_html_json_csv_and_launcher(tmp_path):
    inputs = make_inputs(tmp_path)
    model = dashboard_module.build_dashboard_model(inputs)
    files = dashboard_module.write_dashboard_files(tmp_path / "out", model)

    assert Path(files["dashboard_model_json"]).exists()
    assert Path(files["dashboard_html"]).exists()
    assert Path(files["dashboard_summary_csv"]).exists()
    assert Path(files["open_dashboard_bat"]).exists()

    html_text = Path(files["dashboard_html"]).read_text(encoding="utf-8")
    assert "HQE Forward Paper Dashboard" in html_text
    assert "Paper/simulation only" in html_text
    assert "Broker execution" in html_text
    assert "Real orders" in html_text
    assert "Auto trading" in html_text
    assert "not a profitability claim" in html_text.lower()


def test_dashboard_html_escapes_user_controlled_text(tmp_path):
    inputs = make_inputs(tmp_path)
    model = dashboard_module.build_dashboard_model(inputs)
    model["pe_reason"] = "<script>alert('x')</script>"
    html_text = dashboard_module.render_dashboard_html(model)

    assert "<script>alert" not in html_text
    assert "&lt;script&gt;" in html_text
