from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "hqe_fyers_candle_csv_writer.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_fyers_candle_writer_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_epoch_to_ist_iso():
    module = load_module()
    assert module.epoch_to_ist_iso(1783568700).endswith("+05:30")


def test_normalize_sorts_and_deduplicates():
    module = load_module()
    candles = [
        [1783569000, 2, 3, 1, 2.5, 20],
        [1783568700, 1, 2, 0.5, 1.5, 10],
        [1783569000, 2, 3, 1, 2.5, 20],
    ]
    rows = module.normalize_candles(candles)
    assert len(rows) == 2
    assert rows[0]["datetime"] < rows[1]["datetime"]


def test_write_from_fetch_status(tmp_path):
    module = load_module()
    status = tmp_path / "status.json"
    output = tmp_path / "candles.csv"

    status.write_text(
        json.dumps(
            {
                "history_result": {
                    "rows": 2,
                    "response_redacted": {
                        "s": "ok",
                        "code": 200,
                        "candles": [
                            [1783568700, 1, 2, 0.5, 1.5, 10],
                            [1783569000, 2, 3, 1, 2.5, 20],
                        ],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    result = module.write_from_fetch_status(status, output)
    assert result["write_status"] == "CANDLES_WRITTEN_ATOMICALLY"
    assert result["written_rows"] == 2
    assert result["row_count_match"] is True

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert rows[0]["source"] == "fyers_history_api"


def test_error_response_does_not_overwrite(tmp_path):
    module = load_module()
    status = tmp_path / "status.json"
    output = tmp_path / "candles.csv"
    output.write_text("keep-me", encoding="utf-8")

    status.write_text(
        json.dumps(
            {
                "history_result": {
                    "rows": 0,
                    "response_redacted": {
                        "s": "error",
                        "code": -16,
                        "candles": [],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    result = module.write_from_fetch_status(status, output)
    assert result["write_status"] == "NO_CANDLES_TO_WRITE"
    assert output.read_text(encoding="utf-8") == "keep-me"
