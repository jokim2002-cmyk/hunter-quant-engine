from __future__ import annotations

import csv
import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
SUPERVISOR = SCRIPTS / "run_forward_intraday_paper_supervisor.py"


def load_helper():
    sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("hqe_smc_live_direction")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def candidate() -> dict:
    return {
        "min_dte": 1,
        "min_last_traded_price": 20.0,
        "max_last_traded_price": 200.0,
        "stop_loss_percent": 0.40,
        "target_percent": 1.20,
    }


def index_rows(count: int = 30) -> list[dict]:
    rows = []
    for index in range(count):
        base = 24000.0 + index
        rows.append(
            {
                "timestamp": f"2026-07-13 10:{index:02d}:00",
                "open": base,
                "high": base + 10,
                "low": base - 10,
                "close": base + 2,
                "volume": 1000 + index,
            }
        )
    return rows


def test_decision_mapping_is_bidirectional():
    helper = load_helper()
    assert helper.map_decision("LONG") == "CE_BUY"
    assert helper.map_decision("SHORT") == "PE_BUY"
    assert helper.map_decision("NEUTRAL") == "NO_TRADE"


def test_long_uses_ce_premium(tmp_path, monkeypatch):
    helper = load_helper()
    index_csv = tmp_path / "index.csv"
    premium_csv = tmp_path / "premium.csv"

    write_csv(index_csv, index_rows())
    write_csv(
        premium_csv,
        [
            {
                "timestamp": "2026-07-13 10:29:00",
                "symbol": "NIFTY_TEST_PE",
                "ltp": "95",
                "dte": "2",
            },
            {
                "timestamp": "2026-07-13 10:29:00",
                "symbol": "NIFTY_TEST_CE",
                "ltp": "120",
                "dte": "2",
            },
        ],
    )
    monkeypatch.setattr(
        helper,
        "_run_gate",
        lambda events: ("LONG", "bullish_smc_valid", 200.0),
    )

    result = helper.evaluate_from_csv(
        index_csv,
        premium_csv,
        candidate(),
        er20=0.45,
    )
    assert result["fallback_to_legacy"] is False
    assert result["decision"] == "LONG"
    assert result["side"] == "CE_BUY"
    assert result["signal_generated"] is True
    assert result["entry"] == 120.0


def test_short_uses_pe_premium(tmp_path, monkeypatch):
    helper = load_helper()
    index_csv = tmp_path / "index.csv"
    premium_csv = tmp_path / "premium.csv"

    write_csv(index_csv, index_rows())
    write_csv(
        premium_csv,
        [
            {
                "timestamp": "2026-07-13 10:29:00",
                "symbol": "NIFTY_TEST_CE",
                "ltp": "80",
                "dte": "2",
            },
            {
                "timestamp": "2026-07-13 10:29:00",
                "symbol": "NIFTY_TEST_PE",
                "ltp": "100",
                "dte": "2",
            },
        ],
    )
    monkeypatch.setattr(
        helper,
        "_run_gate",
        lambda events: ("SHORT", "bearish_smc_valid", -200.0),
    )

    result = helper.evaluate_from_csv(
        index_csv,
        premium_csv,
        candidate(),
        er20=0.50,
    )
    assert result["side"] == "PE_BUY"
    assert result["signal_generated"] is True
    assert result["entry"] == 100.0


def test_short_fixture_history_keeps_legacy_compatibility(tmp_path):
    helper = load_helper()
    index_csv = tmp_path / "index.csv"
    premium_csv = tmp_path / "premium.csv"

    write_csv(index_csv, index_rows(count=2))
    write_csv(
        premium_csv,
        [
            {
                "timestamp": "2026-07-13 10:01:00",
                "symbol": "NIFTY_TEST_PE",
                "ltp": "100",
                "dte": "2",
            }
        ],
    )

    result = helper.evaluate_from_csv(
        index_csv,
        premium_csv,
        candidate(),
        er20=0.50,
    )
    assert result["fallback_to_legacy"] is True


def test_supervisor_has_active_smc_bridge_and_legacy_path():
    text = SUPERVISOR.read_text(encoding="utf-8-sig")
    assert "ACTIVE_SMC_CANDIDATE" in text
    assert "evaluate_active_smc_candidate" in text
    assert "evaluate_from_csv" in text
    assert "SMC_BIDIRECTIONAL" in text
    assert "PE_REJECT_INDEX_NOT_FALLING" in text
    assert "OPTION_SIDE=CE_BUY" in text
