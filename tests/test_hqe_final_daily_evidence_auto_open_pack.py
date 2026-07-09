from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hqe_final_daily_evidence_auto_open_pack.py"
spec = importlib.util.spec_from_file_location("hqe_final_daily_evidence_auto_open_pack", MODULE_PATH)
pack = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pack
assert spec.loader is not None
spec.loader.exec_module(pack)


def test_guard_check_blocks_execution_paths() -> None:
    payload = pack.guard_check()
    assert payload["guard_check_status"] == "PASS"
    assert payload["local_files_only"] is True
    assert payload["external_api_calls_executed_by_shortcut_pack"] is False
    assert payload["order_api_invoked_by_shortcut_pack"] is False
    assert payload["broker_execution_invoked_by_shortcut_pack"] is False
    assert payload["auto_trading_started_by_shortcut_pack"] is False
    assert payload["fake_trades_created_by_shortcut_pack"] is False
    assert payload["real_money_automatic"] is False
    assert payload["safety_lock"]["no_real_orders"] is True


def test_candidate_builder_uses_day_number_and_local_paths(tmp_path: Path) -> None:
    candidates = pack.build_evidence_candidates(tmp_path, "2026-07-09", 1)
    filenames = {item["filename"] for item in candidates}
    assert "DAY_001_FORWARD_VALIDATION_DAY_CLOSE.json" in filenames
    assert "DAY_001_PAPER_SIGNAL_NO_TRADE_REASON.json" in filenames
    assert all(item["local_only"] is True for item in candidates)


def test_shortcut_pack_counts_present_and_missing_files(tmp_path: Path) -> None:
    (tmp_path / "DAY_001_FORWARD_VALIDATION_DAY_CLOSE.json").write_text("{}", encoding="utf-8")
    (tmp_path / "FORWARD_VALIDATION_DAY_LEDGER.csv").write_text("date,trade_count\n2026-07-09,0\n", encoding="utf-8")

    payload = pack.build_shortcut_pack(tmp_path, trading_date="2026-07-09", day_number=1, write=False)

    assert payload["shortcut_pack_status"] == "PASS"
    assert payload["decision"] == "DAILY_EVIDENCE_SHORTCUT_PACK_READY_LOCAL_FILES_ONLY"
    assert payload["present_evidence_files_count"] == 2
    assert payload["missing_expected_files_count"] == len(pack.EVIDENCE_PATTERNS) - 2
    assert payload["auto_open_executed_by_pack"] is False
    assert payload["external_api_calls_executed_by_shortcut_pack"] is False


def test_write_emits_status_index_and_manual_opener(tmp_path: Path) -> None:
    (tmp_path / "DAY_001_FORWARD_VALIDATION_DAY_CLOSE.md").write_text("# close", encoding="utf-8")

    payload = pack.build_shortcut_pack(tmp_path, trading_date="2026-07-09", day_number=1, write=True)

    status_json = tmp_path / pack.OUTPUT_STATUS_JSON
    status_md = tmp_path / pack.OUTPUT_STATUS_MD
    index_md = tmp_path / pack.OUTPUT_SHORTCUT_INDEX_MD
    opener_cmd = tmp_path / pack.OUTPUT_SHORTCUT_CMD

    assert status_json.exists()
    assert status_md.exists()
    assert index_md.exists()
    assert opener_cmd.exists()
    assert payload["auto_open_launcher_emitted"] is True
    assert payload["auto_open_executed_by_pack"] is False

    loaded = json.loads(status_json.read_text(encoding="utf-8"))
    assert loaded["shortcut_pack_status"] == "PASS"
    cmd_text = opener_cmd.read_text(encoding="utf-8")
    assert "No trading" in cmd_text
    assert "No broker execution" in cmd_text
    assert "start" in cmd_text


def test_invalid_day_and_date_rejected(tmp_path: Path) -> None:
    try:
        pack.build_shortcut_pack(tmp_path, trading_date="09-07-2026", day_number=1)
    except ValueError as exc:
        assert "YYYY-MM-DD" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("invalid date should fail")

    try:
        pack.build_shortcut_pack(tmp_path, trading_date="2026-07-09", day_number=0)
    except ValueError as exc:
        assert "between 1 and 999" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("invalid day should fail")
