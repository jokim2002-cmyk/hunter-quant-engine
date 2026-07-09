import csv
import importlib.util
import json
import os
import sys
import time
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_dashboard_launcher.py"
SPEC = importlib.util.spec_from_file_location("build_forward_dashboard_launcher", SCRIPT_PATH)
launcher_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = launcher_module
SPEC.loader.exec_module(launcher_module)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def create_evidence_dir(root: Path, name: str, *, day_label: str, opened: int = 1) -> Path:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)

    write_json(
        folder / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json",
        {
            "day_label": day_label,
            "day_status": "HOLD_MORE_DATA_REQUIRED",
            "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
            "gate": "HOLD_MORE_DATA_REQUIRED",
            "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING",
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
                "opened_positions": opened,
                "closed_positions": 0,
                "open_positions_estimated": opened,
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
        folder / "MODULE_133_DAILY_SUMMARY.csv",
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
                "day_label": day_label,
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
        folder / "MODULE_133_EVIDENCE_MANIFEST.csv",
        ["artifact", "path", "present"],
        [
            {"artifact": "daily_pack_json", "path": str(folder / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"), "present": "True"},
            {"artifact": "daily_summary_csv", "path": str(folder / "MODULE_133_DAILY_SUMMARY.csv"), "present": "True"},
        ],
    )

    write_json(
        folder / "MODULE_131_SUPERVISOR_SUMMARY.json",
        {
            "signal_generated": True,
            "event": "POSITION_OPENED",
            "position_state": "OPEN",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        },
    )

    write_json(
        folder / "MODULE_132_AI_REASON_OVERLAY.json",
        {
            "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
            "gate": "HOLD_MORE_DATA_REQUIRED",
            "operator_message": "Paper PE signal logged. Position simulated only. Real order mat lagana.",
        },
    )

    return folder


def test_safety_contract_is_read_only_launcher():
    assert launcher_module.PAPER_ONLY is True
    assert launcher_module.READ_ONLY_LAUNCHER is True
    assert launcher_module.LOCAL_STATIC_HTML_ONLY is True
    assert launcher_module.BROKER_EXECUTION_ALLOWED is False
    assert launcher_module.REAL_ORDERS_ALLOWED is False
    assert launcher_module.REAL_MONEY_ALLOWED is False
    assert launcher_module.AUTO_TRADING_ALLOWED is False
    assert launcher_module.OPTION_SELLING_ALLOWED is False
    assert launcher_module.EXTERNAL_API_ALLOWED is False
    assert launcher_module.PROFITABILITY_CLAIM is False
    launcher_module.assert_safety_contract()


def test_discover_evidence_dirs_selects_latest_by_modified_time(tmp_path):
    older = create_evidence_dir(tmp_path, "HQE_DRY_RUN_001_FORWARD_PAPER_PIPELINE_OLD", day_label="OLD", opened=1)
    newer = create_evidence_dir(tmp_path, "HQE_DRY_RUN_002_NO_SIGNAL_FORWARD_PAPER_PIPELINE_NEW", day_label="NEW", opened=2)

    old_time = time.time() - 1000
    new_time = time.time()
    os.utime(older, (old_time, old_time))
    os.utime(newer, (new_time, new_time))

    discovered = launcher_module.discover_evidence_dirs(tmp_path)
    assert discovered[0] == newer
    assert discovered[1] == older

    resolved = launcher_module.resolve_evidence_dir(tmp_path, None)
    assert resolved == newer


def test_build_launcher_from_explicit_evidence_dir_creates_dashboard(tmp_path):
    evidence = create_evidence_dir(tmp_path / "runs", "HQE_DRY_RUN_001_FORWARD_PAPER_PIPELINE", day_label="DRY_RUN_001", opened=1)
    inputs = launcher_module.LauncherInputs(
        runs_root=tmp_path / "runs",
        evidence_dir=evidence,
        out_dir=tmp_path / "out",
        day_label=None,
    )

    model = launcher_module.build_launcher(inputs)

    assert model["module"] == 135
    assert model["paper_only"] is True
    assert model["read_only_launcher"] is True
    assert model["local_static_html_only"] is True
    assert model["launcher_status"] == "LATEST_EVIDENCE_DASHBOARD_READY"
    assert model["day_label"] == "DRY_RUN_001"
    assert model["dashboard_status"] == "HOLD_MORE_DATA_REQUIRED"
    assert model["opened_positions"] == 1
    assert Path(model["dashboard_html"]).exists()
    assert Path(model["dashboard_model_json"]).exists()


def test_write_launcher_files_creates_model_report_and_open_bat(tmp_path):
    model = {
        "module": 135,
        "module_name": "Dashboard Launcher / Latest Dry-Run Integration",
        "created_at": "2026-07-09T11:00:00",
        "paper_only": True,
        "read_only_launcher": True,
        "local_static_html_only": True,
        "broker_execution_allowed": False,
        "real_orders_allowed": False,
        "real_money_allowed": False,
        "auto_trading_allowed": False,
        "option_selling_allowed": False,
        "external_api_allowed": False,
        "profitability_claim": False,
        "launcher_status": "LATEST_EVIDENCE_DASHBOARD_READY",
        "runs_root": str(tmp_path),
        "evidence_dir": str(tmp_path / "evidence"),
        "day_label": "DRY_RUN_001",
        "dashboard_status": "HOLD_MORE_DATA_REQUIRED",
        "day_status": "HOLD_MORE_DATA_REQUIRED",
        "signal_generated": True,
        "event": "POSITION_OPENED",
        "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
        "gate": "HOLD_MORE_DATA_REQUIRED",
        "position_state": "OPEN",
        "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
        "dashboard_html": str(tmp_path / "dashboard.html"),
        "dashboard_model_json": str(tmp_path / "dashboard.json"),
        "dashboard_summary_csv": str(tmp_path / "dashboard.csv"),
    }

    files = launcher_module.write_launcher_files(tmp_path / "out", model)

    assert Path(files["launcher_model_json"]).exists()
    assert Path(files["launcher_report_md"]).exists()
    assert Path(files["open_latest_dashboard_bat"]).exists()

    report_text = Path(files["launcher_report_md"]).read_text(encoding="utf-8")
    assert "Paper/simulation only: YES" in report_text
    assert "Read-only launcher: YES" in report_text
    assert "Broker execution: NO" in report_text
    assert "not a profitability claim" in report_text.lower()


def test_no_evidence_returns_no_data_model(tmp_path):
    inputs = launcher_module.LauncherInputs(
        runs_root=tmp_path / "empty_runs",
        evidence_dir=None,
        out_dir=tmp_path / "out",
        day_label=None,
    )

    model = launcher_module.build_launcher(inputs)

    assert model["launcher_status"] == "NO_EVIDENCE_FOUND"
    assert model["paper_only"] is True
    assert model["read_only_launcher"] is True
    assert model["dashboard_html"] == ""
