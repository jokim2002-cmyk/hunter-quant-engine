from __future__ import annotations

from src.multi_strategy.adapters.current_smc import (
    CURRENT_SMC_STRATEGY_ID,
    CURRENT_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.adapters.historical_smc import (
    HISTORICAL_SMC_STRATEGY_ID,
    HISTORICAL_SMC_STRATEGY_VERSION,
)
from src.multi_strategy.catalog import build_phase3_registry
from src.multi_strategy.registry import RegistrationStatus


def test_phase3_catalog_has_two_reviewed_registrations():
    registry = build_phase3_registry()
    registrations = registry.list_registrations()

    assert {
        registration.registration_key
        for registration in registrations
    } == {
        (CURRENT_SMC_STRATEGY_ID, CURRENT_SMC_STRATEGY_VERSION),
        (
            HISTORICAL_SMC_STRATEGY_ID,
            HISTORICAL_SMC_STRATEGY_VERSION,
        ),
    }
    assert all(
        registration.status is RegistrationStatus.EXECUTABLE_REVIEWED
        for registration in registrations
    )


def test_catalog_current_adapter_is_not_misrepresented_as_backtest_strategy():
    registry = build_phase3_registry()
    current = registry.create(
        CURRENT_SMC_STRATEGY_ID,
        CURRENT_SMC_STRATEGY_VERSION,
    )

    assert not hasattr(current, "generate")
    assert hasattr(current, "evaluate_from_csv")
