from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def load(name: str):
    path = SCRIPTS / "hqe_market_data_quality_engine.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["datetime", "open", "high", "low", "close", "volume"]
        )
        writer.writerows(rows)


def test_quality_engine_detects_duplicates_gaps_and_invalid_ohlc(tmp_path):
    module = load("quality_issues")
    path = tmp_path / "bad.csv"
    write_csv(
        path,
        [
            ["2026-07-10 09:15:00", 100, 102, 99, 101, 10],
            ["2026-07-10 09:15:00", 101, 103, 100, 102, 11],
            ["2026-07-10 09:30:00", 105, 104, 103, 106, -1],
        ],
    )
    result = module.analyze_csv(path)
    assert result["duplicate_timestamps"] == 1
    assert result["same_day_gaps"] >= 1
    assert result["invalid_ohlc"] == 1
    assert result["negative_volume"] == 1
    assert result["status"] in {"CHECK", "FAILED"}


def test_quality_engine_accepts_clean_file(tmp_path):
    module = load("quality_clean")
    path = tmp_path / "clean.csv"
    write_csv(
        path,
        [
            ["2026-07-10 09:15:00", 100, 102, 99, 101, 10],
            ["2026-07-10 09:20:00", 101, 103, 100, 102, 11],
            ["2026-07-10 09:25:00", 102, 104, 101, 103, 12],
        ],
    )
    result = module.analyze_csv(path)
    assert result["status"] == "PASS"
    assert result["score"] == 100


def test_best_source_prefers_score_then_rows(tmp_path):
    module = load("quality_best_source")
    analyses = [
        {"status": "CHECK", "score": 80, "row_count": 100},
        {"status": "PASS", "score": 100, "row_count": 10},
    ]
    assert module.choose_best_source(analyses)["score"] == 100


def test_quality_guard_locks_execution():
    module = load("quality_guard")
    payload = module.guard_payload()
    assert payload["guard_check_status"] == "PASS"
    assert payload["read_only_scan"] is True
    assert payload["real_orders_enabled"] is False
    assert payload["broker_execution_enabled"] is False
