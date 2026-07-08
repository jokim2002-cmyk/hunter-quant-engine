from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_forward_signal_feed.py"
SPEC = importlib.util.spec_from_file_location("build_forward_signal_feed", MODULE_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_compute_index_er20_states_flags_range_expansion() -> None:
    rows = []
    for minute in range(20):
        rows.append(
            {
                "timestamp": f"2026-07-09 09:{15 + minute:02d}:00",
                "high": "100",
                "low": "90",
            }
        )
    rows.append(
        {
            "timestamp": "2026-07-09 09:35:00",
            "high": "130",
            "low": "90",
        }
    )

    states = MODULE.compute_index_er20_states(rows, min_er20=0.30)

    assert "2026-07-09 09:35:00" in states
    assert states["2026-07-09 09:35:00"].er20 == 4.0


def test_build_forward_signal_feed_creates_only_locked_pe_candidates(tmp_path: Path) -> None:
    index_csv = tmp_path / "index.csv"
    premium_csv = tmp_path / "premium.csv"
    output_csv = tmp_path / "signals.csv"
    report_json = tmp_path / "report.json"
    report_md = tmp_path / "report.md"

    index_rows = []
    for minute in range(20):
        index_rows.append(
            {
                "timestamp": f"2026-07-09 09:{15 + minute:02d}:00",
                "high": "100",
                "low": "90",
            }
        )
    index_rows.append(
        {
            "timestamp": "2026-07-09 09:35:00",
            "high": "130",
            "low": "90",
        }
    )
    _write_csv(index_csv, ["timestamp", "high", "low"], index_rows)

    premium_rows = [
        {
            "timestamp": "2026-07-09 09:35:00",
            "symbol": "NIFTY26JUL24000PE",
            "option_type": "PE",
            "expiry": "2026-07-16",
            "last_traded_price": "100",
        },
        {
            "timestamp": "2026-07-09 09:35:00",
            "symbol": "NIFTY26JUL24000CE",
            "option_type": "CE",
            "expiry": "2026-07-16",
            "last_traded_price": "100",
        },
        {
            "timestamp": "2026-07-09 09:35:00",
            "symbol": "NIFTY26JUL23000PE",
            "option_type": "PE",
            "expiry": "2026-07-16",
            "last_traded_price": "250",
        },
    ]
    _write_csv(
        premium_csv,
        ["timestamp", "symbol", "option_type", "expiry", "last_traded_price"],
        premium_rows,
    )

    status = MODULE.build_forward_signal_feed(
        index_csv=index_csv,
        premium_csv=premium_csv,
        output_csv=output_csv,
        report_json=report_json,
        report_md=report_md,
        only_date="2026-07-09",
        start_time="09:15:00",
        end_time="15:30:00",
    )

    assert status["decision"] == "FORWARD_SIGNAL_FEED_CREATED"
    assert status["signals_created"] == 1
    assert status["rejected_counts"]["not_pe"] == 1
    assert status["rejected_counts"]["premium_outside_range"] == 1

    with output_csv.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["side"] == "PE_BUY"
    assert rows[0]["symbol"] == "NIFTY26JUL24000PE"
    assert rows[0]["dte"] == "7"
    assert rows[0]["rule_match"] == "YES"
    assert rows[0]["manual_override"] == "NO"
    assert "accepted_locked_candidate" in rows[0]["reason"]


def test_build_forward_signal_feed_reports_no_signal_when_no_er20_match(tmp_path: Path) -> None:
    index_csv = tmp_path / "index.csv"
    premium_csv = tmp_path / "premium.csv"
    output_csv = tmp_path / "signals.csv"
    report_json = tmp_path / "report.json"
    report_md = tmp_path / "report.md"

    index_rows = []
    for minute in range(21):
        index_rows.append(
            {
                "timestamp": f"2026-07-09 09:{15 + minute:02d}:00",
                "high": "100",
                "low": "100",
            }
        )
    _write_csv(index_csv, ["timestamp", "high", "low"], index_rows)

    _write_csv(
        premium_csv,
        ["timestamp", "symbol", "option_type", "expiry", "last_traded_price"],
        [
            {
                "timestamp": "2026-07-09 09:35:00",
                "symbol": "NIFTY26JUL24000PE",
                "option_type": "PE",
                "expiry": "2026-07-16",
                "last_traded_price": "100",
            }
        ],
    )

    status = MODULE.build_forward_signal_feed(
        index_csv=index_csv,
        premium_csv=premium_csv,
        output_csv=output_csv,
        report_json=report_json,
        report_md=report_md,
        only_date="2026-07-09",
    )

    assert status["decision"] == "NO_LOCKED_CANDIDATE_SIGNALS_FOUND"
    assert status["signals_created"] == 0

    saved_status = json.loads(report_json.read_text(encoding="utf-8"))
    assert saved_status["safety"]["real_money"] == "NO"
    assert saved_status["safety"]["broker_execution"] == "NO"
