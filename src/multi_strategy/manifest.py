"""Versioned, deterministic HQE strategy manifest and parameter schema."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.multi_strategy.errors import ManifestValidationError

MANIFEST_SCHEMA_VERSION = "1.0.0"
CANONICAL_SIGNALS = ("LONG", "SHORT", "NEUTRAL")
CANONICAL_OPTION_MAPPING = {
    "LONG": "CE_BUY",
    "SHORT": "PE_BUY",
    "NEUTRAL": "NO_TRADE",
}

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_IMPLEMENTATION_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_ALLOWED_PARAMETER_TYPES = {
    "number",
    "integer",
    "boolean",
    "string",
    "choice",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class ParameterSpec:
    """One validated strategy parameter definition."""

    name: str
    value_type: str
    default: Any
    description: str = ""
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[Any, ...] = ()

    def validation_issues(self) -> tuple[str, ...]:
        issues: list[str] = []
        if not _ID_PATTERN.fullmatch(self.name):
            issues.append(
                f"parameter '{self.name}' must be a safe lowercase identifier"
            )
        if self.value_type not in _ALLOWED_PARAMETER_TYPES:
            issues.append(
                f"parameter '{self.name}' has unsupported type "
                f"'{self.value_type}'"
            )
            return tuple(issues)
        minimum_valid = (
            self.minimum is None or _is_number(self.minimum)
        )
        maximum_valid = (
            self.maximum is None or _is_number(self.maximum)
        )
        if not minimum_valid:
            issues.append(
                f"parameter '{self.name}' minimum must be numeric"
            )
        if not maximum_valid:
            issues.append(
                f"parameter '{self.name}' maximum must be numeric"
            )
        if (
            minimum_valid
            and maximum_valid
            and self.minimum is not None
            and self.maximum is not None
            and float(self.minimum) > float(self.maximum)
        ):
            issues.append(
                f"parameter '{self.name}' minimum exceeds maximum"
            )
        if self.value_type == "choice" and not self.choices:
            issues.append(
                f"parameter '{self.name}' must define non-empty choices"
            )
        issues.extend(self.value_issues(self.default, label="default"))
        return tuple(issues)

    def value_issues(
        self,
        value: Any,
        *,
        label: str = "value",
    ) -> tuple[str, ...]:
        issues: list[str] = []
        prefix = f"parameter '{self.name}' {label}"

        if self.value_type == "number":
            valid_type = _is_number(value)
        elif self.value_type == "integer":
            valid_type = isinstance(value, int) and not isinstance(value, bool)
        elif self.value_type == "boolean":
            valid_type = isinstance(value, bool)
        elif self.value_type in {"string", "choice"}:
            valid_type = isinstance(value, str)
        else:
            return (f"{prefix} cannot be validated for unknown type",)

        if not valid_type:
            return (
                f"{prefix} must match type '{self.value_type}'",
            )

        if _is_number(value):
            numeric = float(value)
            if _is_number(self.minimum) and numeric < float(self.minimum):
                issues.append(
                    f"{prefix} is below minimum {self.minimum}"
                )
            if _is_number(self.maximum) and numeric > float(self.maximum):
                issues.append(
                    f"{prefix} exceeds maximum {self.maximum}"
                )

        if self.value_type == "choice" and value not in self.choices:
            issues.append(
                f"{prefix} must be one of {list(self.choices)}"
            )
        return tuple(issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.value_type,
            "default": self.default,
            "description": self.description,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "choices": list(self.choices),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ParameterSpec":
        choices = payload.get("choices", ())
        if not isinstance(choices, (list, tuple)):
            choices = ()
        return cls(
            name=str(payload.get("name", "")),
            value_type=str(payload.get("type", "")),
            default=payload.get("default"),
            description=str(payload.get("description", "")),
            minimum=payload.get("minimum"),
            maximum=payload.get("maximum"),
            choices=tuple(choices),
        )


@dataclass(frozen=True)
class StrategyManifest:
    """Immutable versioned strategy metadata used by all HQE modes."""

    strategy_id: str
    display_name: str
    strategy_version: str
    description: str
    implementation_key: str
    supported_instruments: tuple[str, ...]
    required_timeframe: str
    required_data_columns: tuple[str, ...]
    warmup_bars: int
    parameters: tuple[ParameterSpec, ...]
    state_schema_version: str
    compatibility_version: str
    schema_version: str = MANIFEST_SCHEMA_VERSION
    signal_outputs: tuple[str, ...] = CANONICAL_SIGNALS
    option_mapping: Mapping[str, str] = field(
        default_factory=lambda: dict(CANONICAL_OPTION_MAPPING)
    )
    paper_only: bool = True
    real_orders_allowed: bool = False
    broker_execution_allowed: bool = False
    auto_trading_allowed: bool = False
    real_money_allowed: bool = False
    option_selling_allowed: bool = False

    @property
    def registration_key(self) -> tuple[str, str]:
        return (self.strategy_id, self.strategy_version)

    def validation_issues(self) -> tuple[str, ...]:
        issues: list[str] = []

        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            issues.append(
                "unsupported manifest schema_version "
                f"'{self.schema_version}'"
            )
        if not _ID_PATTERN.fullmatch(self.strategy_id):
            issues.append(
                "strategy_id must be a safe lowercase identifier"
            )
        if not self.display_name.strip():
            issues.append("display_name is required")
        if not _SEMVER_PATTERN.fullmatch(self.strategy_version):
            issues.append("strategy_version must be semantic versioning")
        if not _SEMVER_PATTERN.fullmatch(self.state_schema_version):
            issues.append("state_schema_version must be semantic versioning")
        if not _SEMVER_PATTERN.fullmatch(self.compatibility_version):
            issues.append("compatibility_version must be semantic versioning")
        if not _IMPLEMENTATION_KEY_PATTERN.fullmatch(
            self.implementation_key
        ):
            issues.append("implementation_key is invalid")
        if not self.supported_instruments:
            issues.append("supported_instruments cannot be empty")
        if not self.required_timeframe.strip():
            issues.append("required_timeframe is required")
        if not self.required_data_columns:
            issues.append("required_data_columns cannot be empty")
        if len(set(self.required_data_columns)) != len(
            self.required_data_columns
        ):
            issues.append("required_data_columns contains duplicates")
        if (
            not isinstance(self.warmup_bars, int)
            or isinstance(self.warmup_bars, bool)
            or self.warmup_bars < 0
        ):
            issues.append("warmup_bars must be a non-negative integer")
        if tuple(self.signal_outputs) != CANONICAL_SIGNALS:
            issues.append(
                "signal_outputs must be LONG, SHORT, NEUTRAL in canonical order"
            )
        if dict(self.option_mapping) != CANONICAL_OPTION_MAPPING:
            issues.append("option_mapping must match the canonical mapping")

        safety_values = {
            "paper_only": self.paper_only,
            "real_orders_allowed": self.real_orders_allowed,
            "broker_execution_allowed": self.broker_execution_allowed,
            "auto_trading_allowed": self.auto_trading_allowed,
            "real_money_allowed": self.real_money_allowed,
            "option_selling_allowed": self.option_selling_allowed,
        }
        if safety_values["paper_only"] is not True:
            issues.append("paper_only must remain true")
        for name, value in safety_values.items():
            if name == "paper_only":
                continue
            if value is not False:
                issues.append(f"{name} must remain false")

        names: set[str] = set()
        for parameter in self.parameters:
            if parameter.name in names:
                issues.append(
                    f"duplicate parameter name '{parameter.name}'"
                )
            names.add(parameter.name)
            issues.extend(parameter.validation_issues())

        return tuple(issues)

    def require_valid(self) -> "StrategyManifest":
        issues = self.validation_issues()
        if issues:
            raise ManifestValidationError(issues)
        return self

    def validate_parameters(
        self,
        values: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        supplied = dict(values or {})
        specs = {parameter.name: parameter for parameter in self.parameters}
        issues = [
            f"unknown parameter '{name}'"
            for name in sorted(set(supplied) - set(specs))
        ]
        normalized: dict[str, Any] = {}

        for name, spec in specs.items():
            value = supplied.get(name, spec.default)
            normalized[name] = value
            issues.extend(spec.value_issues(value))

        if issues:
            raise ManifestValidationError(issues)
        return normalized

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "strategy_id": self.strategy_id,
            "display_name": self.display_name,
            "strategy_version": self.strategy_version,
            "description": self.description,
            "implementation_key": self.implementation_key,
            "supported_instruments": list(self.supported_instruments),
            "required_timeframe": self.required_timeframe,
            "required_data_columns": list(self.required_data_columns),
            "warmup_bars": self.warmup_bars,
            "parameters": [
                parameter.to_dict()
                for parameter in self.parameters
            ],
            "state_schema_version": self.state_schema_version,
            "compatibility_version": self.compatibility_version,
            "signal_outputs": list(self.signal_outputs),
            "option_mapping": dict(self.option_mapping),
            "safety": {
                "paper_only": self.paper_only,
                "real_orders_allowed": self.real_orders_allowed,
                "broker_execution_allowed": self.broker_execution_allowed,
                "auto_trading_allowed": self.auto_trading_allowed,
                "real_money_allowed": self.real_money_allowed,
                "option_selling_allowed": self.option_selling_allowed,
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StrategyManifest":
        parameters_payload = payload.get("parameters", ())
        if not isinstance(parameters_payload, (list, tuple)):
            parameters_payload = ()
        safety = payload.get("safety", {})
        if not isinstance(safety, Mapping):
            safety = {}
        option_mapping = payload.get("option_mapping", {})
        if not isinstance(option_mapping, Mapping):
            option_mapping = {}

        supported_instruments = payload.get(
            "supported_instruments",
            (),
        )
        if not isinstance(supported_instruments, (list, tuple)):
            supported_instruments = ()

        required_data_columns = payload.get(
            "required_data_columns",
            (),
        )
        if not isinstance(required_data_columns, (list, tuple)):
            required_data_columns = ()

        signal_outputs = payload.get("signal_outputs", ())
        if not isinstance(signal_outputs, (list, tuple)):
            signal_outputs = ()

        return cls(
            schema_version=str(payload.get("schema_version", "")),
            strategy_id=str(payload.get("strategy_id", "")),
            display_name=str(payload.get("display_name", "")),
            strategy_version=str(payload.get("strategy_version", "")),
            description=str(payload.get("description", "")),
            implementation_key=str(
                payload.get("implementation_key", "")
            ),
            supported_instruments=tuple(
                str(value)
                for value in supported_instruments
            ),
            required_timeframe=str(
                payload.get("required_timeframe", "")
            ),
            required_data_columns=tuple(
                str(value)
                for value in required_data_columns
            ),
            warmup_bars=payload.get("warmup_bars", -1),
            parameters=tuple(
                ParameterSpec.from_dict(item)
                for item in parameters_payload
                if isinstance(item, Mapping)
            ),
            state_schema_version=str(
                payload.get("state_schema_version", "")
            ),
            compatibility_version=str(
                payload.get("compatibility_version", "")
            ),
            signal_outputs=tuple(
                str(value)
                for value in signal_outputs
            ),
            option_mapping={
                str(key): str(value)
                for key, value in option_mapping.items()
            },
            paper_only=safety.get("paper_only", False),
            real_orders_allowed=safety.get(
                "real_orders_allowed",
                True,
            ),
            broker_execution_allowed=safety.get(
                "broker_execution_allowed",
                True,
            ),
            auto_trading_allowed=safety.get(
                "auto_trading_allowed",
                True,
            ),
            real_money_allowed=safety.get(
                "real_money_allowed",
                True,
            ),
            option_selling_allowed=safety.get(
                "option_selling_allowed",
                True,
            ),
        )

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
