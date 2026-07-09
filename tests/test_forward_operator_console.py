
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_operator_console.py"
SPEC = importlib.util.spec_from_file_location("build_forward_operator_console", SCRIPT_PATH)
operator_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = operator_module
SPEC.loader.exec_module(operator_module)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_history_model(path: Path) -> Path:
    write_json(
        path,
        {
            "history_status": "HISTORY_READY",
            "summary": {
                "signal_days": 1,
                "no_signal_days": 1,
                "open_positions_estimated": 1,
                "closed_positions": 0,
                "total_paper_pnl": 0.0,
            },
            "records": [
                {
                    "day_label": "DRY_RUN_001",
                    "day_status": "HOLD_MORE_DATA_REQUIRED",
                    "signal_generated": True,
                    "event": "POSITION_OPENED",
                    "action": "PE_BUY_SIGNAL_ACCEPTED_PAPER_ONLY",
                    "gate": "HOLD_MORE_DATA_REQUIRED",
                    "position_state": "OPEN",
                    "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_FORWARD_TRADES_0_OF_30",
                    "opened_positions": 1,
                    "closed_positions": 0,
                    "open_positions_estimated": 1,
                    "total_paper_pnl": 0.0,
                },
                {
                    "day_label": "DRY_RUN_002_NO_SIGNAL",
                    "day_status": "NO_COMPLETED_TRADES_HOLD_MORE_DATA_REQUIRED",
                    "signal_generated": False,
                    "event": "NO_SIGNAL",
                    "action": "NO_TRADE_SIGNAL_REJECTED_PAPER_ONLY",
                    "gate": "HOLD_MORE_DATA_REQUIRED",
                    "position_state": "FLAT",
                    "ledger_evaluator_status": "HOLD_MORE_DATA_REQUIRED_LEDGER_NOT_FOUND",
                    "opened_positions": 0,
                    "closed_positions": 0,
                    "open_positions_estimated": 0,
                    "total_paper_pnl": 0.0,
                },
            ],
        },
    )
    return path


def test_safety_contract_is_read_only_operator_console():
    assert operator_module.PAPER_ONLY is True
    assert operator_module.READ_ONLY_OPERATOR_CONSOLE is True
    assert operator_module.LOCAL_STATIC_HTML_ONLY is True
    assert operator_module.BROKER_EXECUTION_ALLOWED is False
    assert operator_module.REAL_ORDERS_ALLOWED is False
    assert operator_module.REAL_MONEY_ALLOWED is False
    assert operator_module.AUTO_TRADING_ALLOWED is False
    assert operator_module.OPTION_SELLING_ALLOWED is False
    assert operator_module.EXTERNAL_API_ALLOWED is False
    assert operator_module.PROFITABILITY_CLAIM is False
    operator_module.assert_safety_contract()


def test_operator_console_model_from_history_open_position(tmp_path):
    history_path = create_history_model(tmp_path / "history.json")
    model = operator_module.build_operator_console_model(
        operator_module.OperatorConsoleInputs(
            runs_root=tmp_path,
            out_dir=tmp_path / "out",
            history_model_json=history_path,
            max_items=10,
        )
    )

    assert model["module"] == 137
    assert model["paper_only"] is True
    assert model["read_only_operator_console"] is True
    assert model["local_static_html_only"] is True
    assert model["operator_status"] == "OPEN_PAPER_POSITION_MONITOR"
    assert model["latest_day_label"] == "DRY_RUN_001"
    assert model["summary"]["signal_days"] == 1
    assert model["summary"]["no_signal_days"] == 1
    assert model["broker_execution_allowed"] is False


def test_operator_console_no_data(tmp_path):
    model = operator_module.build_operator_console_model(
        operator_module.OperatorConsoleInputs(
            runs_root=tmp_path / "empty",
            out_dir=tmp_path / "out",
            history_model_json=None,
            max_items=10,
        )
    )

    assert model["operator_status"] == "NO_DATA_LOADED"
    assert model["operator_message"].startswith("No report pack loaded")
    assert model["total_records"] == 0


def test_write_operator_console_files(tmp_path):
    history_path = create_history_model(tmp_path / "history.json")
    model = operator_module.build_operator_console_model(
        operator_module.OperatorConsoleInputs(
            runs_root=tmp_path,
            out_dir=tmp_path / "out",
            history_model_json=history_path,
            max_items=10,
        )
    )
    files = operator_module.write_operator_console_files(tmp_path / "out", model)

    assert Path(files["operator_console_model_json"]).exists()
    assert Path(files["operator_console_html"]).exists()
    assert Path(files["open_operator_console_bat"]).exists()

    html_text = Path(files["operator_console_html"]).read_text(encoding="utf-8")
    assert "HQE Forward Paper Operator Console" in html_text
    assert "Safety Lock" in html_text
    assert "Broker execution" in html_text
    assert "not a profitability claim" in html_text.lower()


def test_operator_console_html_escapes_text(tmp_path):
    history_path = create_history_model(tmp_path / "history.json")
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    payload["records"][0]["day_label"] = "<script>alert(1)</script>"
    write_json(history_path, payload)

    model = operator_module.build_operator_console_model(
        operator_module.OperatorConsoleInputs(
            runs_root=tmp_path,
            out_dir=tmp_path / "out",
            history_model_json=history_path,
            max_items=10,
        )
    )
    html_text = operator_module.render_operator_console_html(model)

    assert "<script>alert" not in html_text
    assert "&lt;script&gt;" in html_text
