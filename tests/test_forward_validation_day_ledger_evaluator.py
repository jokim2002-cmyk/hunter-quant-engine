from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_forward_validation_day_ledger import (  # noqa: E402
    evaluate_workspace,
    write_outputs,
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]], *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_zero_trade_day_counts_observed_but_not_valid_trade_day(tmp_path: Path) -> None:
    workspace = tmp_path / "forward"
    workspace.mkdir()
    write_csv(
        workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["date", "day_number", "day_status", "trade_count", "safety_ok", "candidate_tuning", "manual_override"],
        [
            {
                "date": "2026-07-09",
                "day_number": 1,
                "day_status": "ZERO_TRADE_DAY_RECORDED",
                "trade_count": 0,
                "safety_ok": "YES",
                "candidate_tuning": "NO",
                "manual_override": "NO",
            }
        ],
        encoding="utf-8-sig",
    )
    write_csv(
        workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv",
        ["trading_date", "expiry_date", "net"],
        [],
    )

    result = evaluate_workspace(workspace)

    assert result.evaluation_status == "PASS"
    assert result.decision == "HOLD_MORE_DATA_REQUIRED"
    assert result.observed_session_days == 1
    assert result.valid_paper_trade_days == 0
    assert result.actual_paper_trades == 0
    assert result.distinct_expiry_weeks == 0
    assert result.cumulative_forward_net == 0


def test_valid_trade_days_require_trade_count_positive_and_actual_trades_stay_from_rows(tmp_path: Path) -> None:
    workspace = tmp_path / "forward"
    workspace.mkdir()
    write_csv(
        workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["trading_date", "day_number", "trade_count", "safety_ok", "candidate_tuning", "manual_override"],
        [
            {"trading_date": "2026-07-09", "day_number": 1, "trade_count": 0, "safety_ok": "YES", "candidate_tuning": "NO", "manual_override": "NO"},
            {"trading_date": "2026-07-10", "day_number": 2, "trade_count": 2, "safety_ok": "YES", "candidate_tuning": "NO", "manual_override": "NO"},
        ],
    )
    write_csv(
        workspace / "FORWARD_VALIDATION_MASTER_LEDGER.csv",
        ["trading_date", "expiry_date", "net"],
        [
            {"trading_date": "2026-07-10", "expiry_date": "2026-07-16", "net": "100.50"},
            {"trading_date": "2026-07-10", "expiry_date": "2026-07-16", "net": "-50.25"},
        ],
    )

    result = evaluate_workspace(workspace)

    assert result.observed_session_days == 2
    assert result.valid_paper_trade_days == 1
    assert result.actual_paper_trades == 2
    assert result.distinct_expiry_weeks == 1
    assert result.cumulative_forward_net == 50.25
    assert result.decision == "HOLD_MORE_DATA_REQUIRED"


def test_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    workspace = tmp_path / "forward"
    workspace.mkdir()
    write_csv(
        workspace / "FORWARD_VALIDATION_DAY_LEDGER.csv",
        ["date", "trade_count", "safety_ok", "candidate_tuning", "manual_override"],
        [{"date": "2026-07-09", "trade_count": 0, "safety_ok": "YES", "candidate_tuning": "NO", "manual_override": "NO"}],
    )

    result = evaluate_workspace(workspace)
    json_path, md_path = write_outputs(workspace, result)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["observed_session_days"] == 1
    assert payload["valid_paper_trade_days"] == 0
    assert payload["safety_lock"]["no_real_orders"] is True
    assert "This is not a profitability claim" in md_path.read_text(encoding="utf-8")

