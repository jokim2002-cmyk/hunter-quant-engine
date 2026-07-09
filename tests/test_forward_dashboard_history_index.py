
import importlib.util
import json
import os
import sys
import time
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_dashboard_history_index.py"
SPEC = importlib.util.spec_from_file_location("build_forward_dashboard_history_index", SCRIPT_PATH)
history_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = history_module
SPEC.loader.exec_module(history_module)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_pack(root: Path, name: str, *, day_label: str, signal: bool, opened: int, pnl: float) -> Path:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)

    write_json(
        folder / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json",
        {
            "day_label": day_label,
            "day_status": "HOLD_MORE_DATA_REQUIRED",
            "locked_candidate": "ER20_GE_030_PE_ONLY_DTE_GE_1_LTP_20_200_SL040_TGT120",
            "signal_generated": signal,
            "event": "POSITION_OPENED" if signal else "NO_SIGNAL",
            "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY" if signal else "NO_TRADE_SIGNAL_REJECTED_PAPER_ONLY",
            "gate": "HOLD_MORE_DATA_REQUIRED",
            "pe_reason": "ER20_OK(1.0000); PE_OK_INDEX_FALLING" if signal else "PE_REJECT_INDEX_NOT_FALLING",
            "entry": 100.0 if signal else "",
            "stop_loss": 60.0 if signal else "",
            "target": 220.0 if signal else "",
            "exit_reason": "",
            "paper_pnl": pnl,
            "position_state": "OPEN" if signal else "FLAT",
            "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
            "ledger_stats": {
                "opened_positions": opened,
                "closed_positions": 0,
                "open_positions_estimated": opened,
                "wins": 0,
                "losses": 0,
                "flats": 0,
                "total_paper_pnl": pnl,
                "average_closed_trade_paper_pnl": 0.0,
            },
            "evidence_counts": {
                "reason_log_rows": 1,
                "ledger_rows": opened,
                "overlay_audit_rows": 1,
            },
        },
    )
    (folder / "MODULE_133_DAILY_PAPER_TRADING_REPORT.md").write_text("# Daily report\n", encoding="utf-8")
    (folder / "MODULE_133_DAILY_SUMMARY.csv").write_text("day_label,day_status\n", encoding="utf-8")
    (folder / "MODULE_133_EVIDENCE_MANIFEST.csv").write_text("artifact,path,present\n", encoding="utf-8")
    return folder


def test_safety_contract_is_read_only_history_index():
    assert history_module.PAPER_ONLY is True
    assert history_module.READ_ONLY_HISTORY_INDEX is True
    assert history_module.LOCAL_STATIC_HTML_ONLY is True
    assert history_module.BROKER_EXECUTION_ALLOWED is False
    assert history_module.REAL_ORDERS_ALLOWED is False
    assert history_module.REAL_MONEY_ALLOWED is False
    assert history_module.AUTO_TRADING_ALLOWED is False
    assert history_module.OPTION_SELLING_ALLOWED is False
    assert history_module.EXTERNAL_API_ALLOWED is False
    assert history_module.PROFITABILITY_CLAIM is False
    history_module.assert_safety_contract()


def test_discover_daily_pack_paths_sorts_by_modified_time(tmp_path):
    older = create_pack(tmp_path, "old_pack", day_label="OLD", signal=False, opened=0, pnl=0.0)
    newer = create_pack(tmp_path, "new_pack", day_label="NEW", signal=True, opened=1, pnl=10.0)

    old_pack = older / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
    new_pack = newer / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"

    old_time = time.time() - 1000
    new_time = time.time()
    os.utime(old_pack, (old_time, old_time))
    os.utime(new_pack, (new_time, new_time))

    discovered = history_module.discover_daily_pack_paths(tmp_path)

    assert discovered[0] == new_pack
    assert discovered[1] == old_pack


def test_build_history_model_aggregates_multiple_packs(tmp_path):
    create_pack(tmp_path, "pack_1", day_label="DAY_001", signal=True, opened=1, pnl=0.0)
    create_pack(tmp_path, "pack_2", day_label="DAY_002", signal=False, opened=0, pnl=0.0)

    model = history_module.build_history_model(
        history_module.HistoryInputs(runs_root=tmp_path, out_dir=tmp_path / "out", max_items=10)
    )

    assert model["module"] == 136
    assert model["paper_only"] is True
    assert model["read_only_history_index"] is True
    assert model["local_static_html_only"] is True
    assert model["history_status"] == "HISTORY_READY"
    assert model["total_records"] == 2
    assert model["summary"]["signal_days"] == 1
    assert model["summary"]["no_signal_days"] == 1
    assert model["summary"]["open_positions_estimated"] == 1


def test_write_history_files_creates_html_json_csv_and_open_bat(tmp_path):
    create_pack(tmp_path, "pack_1", day_label="DAY_001", signal=True, opened=1, pnl=0.0)
    model = history_module.build_history_model(
        history_module.HistoryInputs(runs_root=tmp_path, out_dir=tmp_path / "out", max_items=10)
    )

    files = history_module.write_history_files(tmp_path / "out", model)

    assert Path(files["history_model_json"]).exists()
    assert Path(files["history_index_html"]).exists()
    assert Path(files["history_index_csv"]).exists()
    assert Path(files["open_history_index_bat"]).exists()

    html_text = Path(files["history_index_html"]).read_text(encoding="utf-8")
    assert "HQE Forward Paper History Index" in html_text
    assert "Paper/simulation only" in html_text
    assert "No broker execution" in html_text
    assert "not a profitability claim" in html_text.lower()


def test_history_html_escapes_pack_text(tmp_path):
    folder = create_pack(tmp_path, "pack_xss", day_label="<script>alert(1)</script>", signal=True, opened=1, pnl=0.0)
    pack_path = folder / "MODULE_133_DAILY_PAPER_TRADING_REPORT_PACK.json"
    payload = json.loads(pack_path.read_text(encoding="utf-8"))
    payload["action"] = "<script>alert('x')</script>"
    write_json(pack_path, payload)

    model = history_module.build_history_model(
        history_module.HistoryInputs(runs_root=tmp_path, out_dir=tmp_path / "out", max_items=10)
    )
    html_text = history_module.render_history_html(model)

    assert "<script>alert" not in html_text
    assert "&lt;script&gt;" in html_text
