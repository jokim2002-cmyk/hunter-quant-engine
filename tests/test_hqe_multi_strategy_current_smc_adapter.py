from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts import hqe_smc_live_direction as legacy
from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_IMPLEMENTATION_KEY,
    CurrentSmcCompatibilityAdapter,
    build_current_smc_adapter,
    current_smc_manifest,
)
from src.multi_strategy.errors import ManifestValidationError
from src.multi_strategy.registry import (
    RegistrationStatus,
    StrategyRegistry,
)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


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


def both_sides() -> list[dict]:
    return [
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
    ]


def evaluate_pair(
    tmp_path: Path,
    monkeypatch,
    gate_result: tuple[str, str, float | None],
    *,
    er20: float | None = 0.50,
    premiums: list[dict] | None = None,
    count: int = 30,
):
    index_csv = tmp_path / "index.csv"
    premium_csv = tmp_path / "premium.csv"
    write_csv(index_csv, index_rows(count))
    write_csv(premium_csv, premiums or both_sides())
    monkeypatch.setattr(legacy, "_run_gate", lambda events: gate_result)

    adapter = CurrentSmcCompatibilityAdapter()
    expected = legacy.evaluate_from_csv(
        index_csv,
        premium_csv,
        adapter.candidate,
        er20,
    )
    actual = adapter.evaluate_from_csv(index_csv, premium_csv, er20)
    return expected, actual


def test_manifest_is_valid_and_er20_threshold_is_fixed():
    manifest = current_smc_manifest()
    manifest.require_valid()

    assert manifest.implementation_key == CURRENT_SMC_IMPLEMENTATION_KEY
    assert manifest.validate_parameters()["er20_min"] == 0.30
    with pytest.raises(
        ManifestValidationError,
        match="exceeds maximum",
    ):
        manifest.validate_parameters({"er20_min": 0.31})


def test_reviewed_registry_factory_builds_adapter():
    manifest = current_smc_manifest()
    registry = StrategyRegistry(
        {CURRENT_SMC_IMPLEMENTATION_KEY: build_current_smc_adapter}
    )
    registration = registry.register(manifest)
    adapter = registry.create(
        manifest.strategy_id,
        manifest.strategy_version,
    )

    assert registration.status is RegistrationStatus.EXECUTABLE_REVIEWED
    assert isinstance(adapter, CurrentSmcCompatibilityAdapter)


def test_long_decision_preserves_exact_legacy_payload(tmp_path, monkeypatch):
    expected, actual = evaluate_pair(
        tmp_path,
        monkeypatch,
        ("LONG", "bullish_smc_valid", 200.0),
    )

    assert actual.to_legacy_payload() == expected
    assert actual.signal == "LONG"
    assert actual.option_side == "CE_BUY"
    assert actual.entry_eligible is True
    assert actual.entry == 120.0
    assert actual.stop_loss == 72.0
    assert actual.target == 264.0


def test_short_decision_preserves_exact_legacy_payload(tmp_path, monkeypatch):
    expected, actual = evaluate_pair(
        tmp_path,
        monkeypatch,
        ("SHORT", "bearish_smc_valid", -200.0),
    )

    assert actual.to_legacy_payload() == expected
    assert actual.signal == "SHORT"
    assert actual.option_side == "PE_BUY"
    assert actual.entry_eligible is True
    assert actual.entry == 95.0


def test_neutral_decision_preserves_no_trade(tmp_path, monkeypatch):
    expected, actual = evaluate_pair(
        tmp_path,
        monkeypatch,
        ("NEUTRAL", "no_smc_setup", 0.0),
    )

    assert actual.to_legacy_payload() == expected
    assert actual.signal == "NEUTRAL"
    assert actual.option_side == "NO_TRADE"
    assert actual.entry_eligible is False
    assert actual.fallback_to_legacy is False


def test_er20_rejection_keeps_direction_but_blocks_entry(
    tmp_path,
    monkeypatch,
):
    expected, actual = evaluate_pair(
        tmp_path,
        monkeypatch,
        ("LONG", "bullish_smc_valid", 200.0),
        er20=0.20,
    )

    assert actual.to_legacy_payload() == expected
    assert actual.signal == "LONG"
    assert actual.option_side == "CE_BUY"
    assert actual.entry_eligible is False
    assert "ER20_REJECT_LT_0.30" in actual.reason_text


def test_incomplete_premium_data_is_explicit_legacy_fallback(
    tmp_path,
    monkeypatch,
):
    pe_only = [
        {
            "timestamp": "2026-07-13 10:29:00",
            "symbol": "NIFTY_TEST_PE",
            "ltp": "95",
            "dte": "2",
        }
    ]
    expected, actual = evaluate_pair(
        tmp_path,
        monkeypatch,
        ("LONG", "unused", 200.0),
        premiums=pe_only,
    )

    assert actual.to_legacy_payload() == expected
    assert actual.signal == "NEUTRAL"
    assert actual.option_side == "PE_BUY"
    assert actual.entry_eligible is False
    assert actual.fallback_to_legacy is True
    assert "BIDIRECTIONAL_PREMIUM_DATA_INCOMPLETE" in actual.reason_text


def test_insufficient_history_is_explicit_legacy_fallback(
    tmp_path,
    monkeypatch,
):
    expected, actual = evaluate_pair(
        tmp_path,
        monkeypatch,
        ("LONG", "unused", 200.0),
        count=2,
    )

    assert actual.to_legacy_payload() == expected
    assert actual.signal == "NEUTRAL"
    assert actual.option_side == "PE_BUY"
    assert actual.fallback_to_legacy is True


def test_parameters_hash_is_deterministic_and_candidate_is_normalized():
    first = CurrentSmcCompatibilityAdapter()
    second = CurrentSmcCompatibilityAdapter(
        {
            "target_percent": 1.20,
            "minimum_ltp": 20.0,
            "maximum_ltp": 200.0,
            "minimum_dte": 1,
            "stop_loss_percent": 0.40,
            "er20_min": 0.30,
        }
    )

    assert first.parameters_hash == second.parameters_hash
    assert first.candidate == {
        "min_dte": 1,
        "min_last_traded_price": 20.0,
        "max_last_traded_price": 200.0,
        "stop_loss_percent": 0.40,
        "target_percent": 1.20,
    }


def test_invalid_ltp_range_fails_closed():
    with pytest.raises(
        ManifestValidationError,
        match="maximum_ltp",
    ):
        CurrentSmcCompatibilityAdapter(
            {
                "minimum_ltp": 250.0,
                "maximum_ltp": 200.0,
            }
        )
