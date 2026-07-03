"""
Base Setup Validator Tests
"""

import pytest

from src.strategy.setup_validators.base_setup_validator import BaseSetupValidator


class DummySetupValidator(BaseSetupValidator[object]):
    def is_valid(
        self,
        result: object,
    ) -> bool:
        return result is not None


def test_base_setup_validator_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseSetupValidator()


def test_dummy_setup_validator_implements_base_setup_validator_contract():
    validator = DummySetupValidator()

    assert isinstance(validator, BaseSetupValidator)


def test_dummy_setup_validator_returns_true_for_valid_result():
    validator = DummySetupValidator()

    assert validator.is_valid(object()) is True


def test_dummy_setup_validator_returns_false_for_invalid_result():
    validator = DummySetupValidator()

    assert validator.is_valid(None) is False
